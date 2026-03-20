import type { AnyMessageContent, WAMessage } from '@whiskeysockets/baileys';
import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import type WhatsAppPort from '../ports/WhatsAppPort.js';
import MediaHandler from './MediaHandler.js';
import { Sentry } from '../infra/Sentry.js';

interface WSMessage {
  id: string;
  type: string;
  method?: string;
  data?: Record<string, unknown>;
}

interface PendingRequest {
  resolve: (value: WSMessage) => void;
  reject: (reason: Error) => void;
  timer: ReturnType<typeof setTimeout>;
}

export default class PythonBridge {
  private ws: WebSocket | null = null;
  private pending = new Map<string, PendingRequest>();
  private pendingBinary = new Map<string, Buffer[]>();
  private messageStore = new Map<string, WAMessage>();
  private reconnectDelay = 1000;
  private readonly maxReconnectDelay = 30000;
  private readonly url: string;
  private whatsapp: WhatsAppPort | null = null;
  private mediaHandler: MediaHandler | null = null;
  private shouldReconnect = true;

  constructor(url?: string) {
    this.url = url ?? process.env.PYTHON_BRIDGE_URL ?? 'ws://python-core:8000/ws';
  }

  setWhatsApp(whatsapp: WhatsAppPort): void {
    this.whatsapp = whatsapp;
    this.mediaHandler = new MediaHandler(whatsapp);
  }

  connect(): void {
    if (this.ws) return;
    this.shouldReconnect = true;

    try {
      this.ws = new WebSocket(this.url);
    } catch {
      this.scheduleReconnect();
      return;
    }

    this.ws.addEventListener('open', () => {
      Sentry.logger.info('PythonBridge connected');
      this.reconnectDelay = 1000;
    });

    this.ws.addEventListener('message', (event) => {
      void this.handleMessage(event);
    });

    this.ws.addEventListener('close', () => {
      Sentry.logger.warn('PythonBridge disconnected');
      this.ws = null;
      this.rejectAllPending('WebSocket closed');
      this.scheduleReconnect();
    });

    this.ws.addEventListener('error', () => {
      // close event will fire after this, which handles reconnection
    });
  }

  disconnect(): void {
    this.shouldReconnect = false;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.rejectAllPending('Bridge disconnected');
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  async sendCommand(data: CommandData): Promise<Message[] | null> {
    if (!this.isConnected) return null;

    const id = crypto.randomUUID();
    const messageId = data.key.id ?? null;
    const mediaInfo = this.mediaHandler?.detectMedia(data) ?? null;

    if (messageId) {
      this.messageStore.set(messageId, data as WAMessage);
    }

    const msg: WSMessage = {
      id,
      type: 'command',
      data: {
        text: data.text,
        jid: data.key.remoteJid!,
        sender_jid: (data.key.participant ?? data.key.remoteJid)!,
        participant: data.key.participant ?? null,
        is_group: data.key.remoteJid?.includes('g.us') ?? false,
        expiration: data.expiration ?? null,
        mentioned_jids: data.message?.extendedTextMessage?.contextInfo?.mentionedJid ?? [],
        quoted_message_id: data.message?.extendedTextMessage?.contextInfo?.stanzaId ?? null,
        message_id: messageId,
        push_name: data.pushName ?? null,
        media_type: mediaInfo?.type ?? null,
        media_source: mediaInfo?.source ?? null,
        media_is_animated: mediaInfo?.isAnimated ?? false,
        media_caption: mediaInfo?.caption ?? null,
      },
    };

    try {
      const response = await this.sendAndWait(id, msg);

      if (response.type === 'no_match') return null;

      if (response.type === 'error') {
        const errorMsg = (response.data?.message as string) ?? 'Python command failed';
        throw new Error(errorMsg);
      }

      if (response.type === 'command_response') {
        return this.deserializeMessages(id, response);
      }

      return null;
    } finally {
      if (messageId) {
        this.messageStore.delete(messageId);
      }
    }
  }

  private async handleMessage(event: MessageEvent): Promise<void> {
    if (typeof event.data !== 'string') {
      // Binary frame — associate with the first pending binary response
      const raw = event.data instanceof Blob ? await event.data.arrayBuffer() : event.data;
      const buffer = Buffer.from(raw);
      for (const [, buffers] of this.pendingBinary) {
        buffers.push(buffer);
        break;
      }
      return;
    }

    const msg = JSON.parse(event.data) as WSMessage;

    if (msg.type === 'wa_call') {
      await this.handleWaCall(msg);
      return;
    }

    const pending = this.pending.get(msg.id);
    if (pending) {
      clearTimeout(pending.timer);
      this.pending.delete(msg.id);
      pending.resolve(msg);
    }
  }

  private async handleWaCall(msg: WSMessage): Promise<void> {
    if (!this.whatsapp || !this.ws) return;

    try {
      const result = await this.executeWaMethod(msg.method!, msg.data ?? {});
      this.ws.send(JSON.stringify({ id: msg.id, type: 'wa_result', data: result }));
    } catch (error) {
      this.ws.send(
        JSON.stringify({
          id: msg.id,
          type: 'error',
          data: { message: String(error), code: 'WA_CALL_ERROR' },
        }),
      );
    }
  }

  private async executeWaMethod(
    method: string,
    data: Record<string, unknown>,
  ): Promise<Record<string, unknown>> {
    if (!this.whatsapp) throw new Error('WhatsApp not available');

    switch (method) {
      case 'group_metadata': {
        const metadata = await this.whatsapp.groupMetadata(data.jid as string);
        return metadata as unknown as Record<string, unknown>;
      }
      case 'group_participants_update': {
        const results = await this.whatsapp.groupParticipantsUpdate(
          data.jid as string,
          data.participants as string[],
          data.action as 'add' | 'remove' | 'promote' | 'demote',
        );
        return { results };
      }
      case 'on_whatsapp': {
        const results = await this.whatsapp.onWhatsApp(...(data.jids as string[]));
        return { results };
      }
      case 'send_message': {
        const result = await this.whatsapp.sendMessage(
          data.jid as string,
          data.content as AnyMessageContent,
          data.options as Record<string, unknown> | undefined,
        );
        return (result ?? {}) as Record<string, unknown>;
      }
      case 'group_update_subject':
        await this.whatsapp.groupUpdateSubject(data.jid as string, data.subject as string);
        return {};
      case 'group_update_description':
        await this.whatsapp.groupUpdateDescription(data.jid as string, data.description as string);
        return {};
      case 'send_presence_update':
        await this.whatsapp.sendPresenceUpdate(
          data.type as 'available' | 'composing' | 'recording' | 'paused' | 'unavailable',
          data.jid as string,
        );
        return {};
      case 'download_media': {
        if (!this.mediaHandler) throw new Error('MediaHandler not available');
        const messageId = data.message_id as string;
        const stored = this.messageStore.get(messageId);
        if (!stored) throw new Error(`Message ${messageId} not found in store`);
        const buffer = await this.mediaHandler.downloadMedia(stored, data.source as string);
        return { buffer: buffer.toString('base64') };
      }
      case 'create_sticker': {
        if (!this.mediaHandler) throw new Error('MediaHandler not available');
        const inputBuffer = Buffer.from(data.buffer as string, 'base64');
        const stickerBuffer = await this.mediaHandler.createSticker(
          inputBuffer,
          (data.type as string) || 'full',
        );
        return { buffer: stickerBuffer.toString('base64') };
      }
      default:
        throw new Error(`Unknown wa_call method: ${method}`);
    }
  }

  private deserializeMessages(requestId: string, response: WSMessage): Message[] {
    const msgs = (response.data?.messages as Array<Record<string, unknown>>) ?? [];
    const buffers = this.pendingBinary.get(requestId) ?? [];
    this.pendingBinary.delete(requestId);

    let bufferIdx = 0;
    return msgs.map((m) => {
      const contentData = m.content as Record<string, unknown>;
      const contentType = contentData.type as string;
      const jid = m.jid as string;

      let content: AnyMessageContent;

      const caption = contentData.caption as string | undefined;

      switch (contentType) {
        case 'text':
          content = contentData.mentions
            ? { text: contentData.text as string, mentions: contentData.mentions as string[] }
            : { text: contentData.text as string };
          break;
        case 'image':
          content = {
            image: { url: contentData.url as string },
            viewOnce: contentData.view_once as boolean,
            caption,
          };
          break;
        case 'image_buffer':
          content = {
            image: buffers[bufferIdx++] ?? Buffer.alloc(0),
            viewOnce: contentData.view_once as boolean,
            caption,
          };
          break;
        case 'video':
          content = {
            video: { url: contentData.url as string },
            viewOnce: contentData.view_once as boolean,
            caption,
          };
          break;
        case 'video_buffer':
          content = {
            video: buffers[bufferIdx++] ?? Buffer.alloc(0),
            viewOnce: contentData.view_once as boolean,
            gifPlayback: (contentData.gif_playback as boolean) ?? false,
            caption,
          };
          break;
        case 'audio':
          content = {
            audio: { url: contentData.url as string },
            viewOnce: contentData.view_once as boolean,
            mimetype: (contentData.mimetype as string) ?? 'audio/mp4',
          };
          break;
        case 'audio_buffer':
          content = {
            audio: buffers[bufferIdx++] ?? Buffer.alloc(0),
            mimetype: (contentData.mimetype as string) ?? 'audio/mp4',
          };
          break;
        case 'sticker':
          content = { sticker: buffers[bufferIdx++] ?? Buffer.alloc(0) };
          break;
        case 'raw':
          content = contentData.content as AnyMessageContent;
          break;
        default:
          content = { text: `Unknown content type: ${contentType}` };
      }

      const message: Message = { jid, content };

      if (m.quoted_message_id) {
        message.options = {
          ...message.options,
          quoted: { key: { id: m.quoted_message_id as string } } as WAMessage,
        };
      }
      if (m.expiration) {
        message.options = {
          ...message.options,
          ephemeralExpiration: m.expiration as number,
        };
      }

      return message;
    });
  }

  private sendAndWait(id: string, msg: WSMessage, timeout = 60000): Promise<WSMessage> {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        this.pendingBinary.delete(id);
        reject(new Error(`PythonBridge timeout for ${id}`));
      }, timeout);

      this.pending.set(id, { resolve, reject, timer });
      this.pendingBinary.set(id, []);
      this.ws!.send(JSON.stringify(msg));
    });
  }

  private scheduleReconnect(): void {
    if (!this.shouldReconnect) return;

    setTimeout(() => {
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
      this.connect();
    }, this.reconnectDelay);
  }

  private rejectAllPending(reason: string): void {
    for (const [, p] of this.pending) {
      clearTimeout(p.timer);
      p.reject(new Error(reason));
    }
    this.pending.clear();
    this.pendingBinary.clear();
  }
}
