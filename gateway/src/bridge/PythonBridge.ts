import type { AnyMessageContent, WAMessage } from '@whiskeysockets/baileys';
import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import type WhatsAppPort from '../ports/WhatsAppPort.js';
import MediaHandler from './MediaHandler.js';
import injectStickerExif from '../utils/StickerExif.js';
import { Sentry } from '../infra/Sentry.js';
import logger from '../infra/Logger.js';

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
  private ackCallbacks = new Map<string, () => void | Promise<void>>();
  private messageStore = new Map<string, WAMessage>();
  private reconnectDelay = 1000;
  private readonly maxReconnectDelay = 30000;
  private readonly url: string;
  private whatsapp: WhatsAppPort | null = null;
  private mediaHandler: MediaHandler | null = null;
  private shouldReconnect = true;

  constructor(url?: string) {
    this.url = url ?? process.env.PYTHON_BRIDGE_URL ?? 'ws://bot:8000/ws';
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
      this.ws.binaryType = 'arraybuffer';
    } catch {
      this.scheduleReconnect();
      return;
    }

    this.ws.addEventListener('open', () => {
      logger.info({ event: 'python_bridge_connected' });
      this.reconnectDelay = 1000;
    });

    this.ws.addEventListener('message', (event) => {
      void this.handleMessage(event);
    });

    this.ws.addEventListener('close', () => {
      logger.warn({ event: 'python_bridge_disconnected' });
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

  async sendCommand(
    data: CommandData,
    onAck?: () => void | Promise<void>,
  ): Promise<Message[] | null> {
    if (!this.isConnected) return null;

    const id = crypto.randomUUID();
    const messageId = data.key.id ?? null;
    const mediaInfo = this.mediaHandler?.detectMedia(data) ?? null;

    if (messageId) {
      this.messageStore.set(messageId, data as WAMessage);
    }

    let mediaBuffer: Buffer | null = null;
    if (mediaInfo && this.mediaHandler) {
      try {
        mediaBuffer = await this.mediaHandler.downloadMedia(data as WAMessage, mediaInfo.source);
      } catch (error) {
        logger.warn({
          event: 'media_download_failed',
          msg_id: id,
          jid: data.key.remoteJid,
          error: String(error),
        });
      }
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
        mentioned_jids:
          data.message?.extendedTextMessage?.contextInfo?.mentionedJid ??
          (data.message as any)?.conversationMessage?.contextInfo?.mentionedJid ??
          [],
        quoted_message_id: data.message?.extendedTextMessage?.contextInfo?.stanzaId ?? null,
        quoted_text: (() => {
          const quoted = data.message?.extendedTextMessage?.contextInfo?.quotedMessage;
          if (!quoted) return null;
          return quoted.conversation ?? quoted.extendedTextMessage?.text ?? null;
        })(),
        message_id: messageId,
        push_name: data.pushName ?? null,
        media_type: mediaInfo?.type ?? null,
        media_source: mediaInfo?.source ?? null,
        media_is_animated: mediaInfo?.isAnimated ?? false,
        media_caption: mediaInfo?.caption ?? null,
        media_buffer_size: mediaBuffer?.length ?? 0,
      },
    };

    if (onAck) {
      this.ackCallbacks.set(id, onAck);
    }

    try {
      if (mediaBuffer) {
        this.ws!.send(mediaBuffer);
      }
      const response = await this.sendAndWait(id, msg);

      if (response.type === 'no_match') return null;

      if (response.type === 'error') {
        const errorMsg = (response.data?.message as string) ?? 'Python command failed';
        throw new Error(errorMsg);
      }

      if (response.type === 'command_response') {
        return await this.deserializeMessages(id, response);
      }

      return null;
    } finally {
      this.pendingBinary.delete(id);
      this.ackCallbacks.delete(id);
      if (messageId) {
        this.messageStore.delete(messageId);
      }
    }
  }

  sendGroupEvent(data: Record<string, unknown>): void {
    if (!this.isConnected) return;
    this.ws!.send(
      JSON.stringify({
        id: crypto.randomUUID(),
        type: 'group_event',
        data,
      }),
    );
  }

  private static readonly UUID_LEN = 36;

  private async handleMessage(event: MessageEvent): Promise<void> {
    if (typeof event.data !== 'string') {
      // Binary frames are prefixed with "<uuid>:" (37 bytes) so they can be routed
      // to the correct pending request when multiple commands execute concurrently.
      const raw = Buffer.from(event.data as ArrayBuffer);
      if (raw.length > PythonBridge.UUID_LEN && raw[PythonBridge.UUID_LEN] === 0x3a) {
        const requestId = raw.subarray(0, PythonBridge.UUID_LEN).toString('ascii');
        this.pendingBinary.get(requestId)?.push(raw.subarray(PythonBridge.UUID_LEN + 1));
      }
      return;
    }

    const msg = JSON.parse(event.data) as WSMessage;

    if (msg.type === 'command_ack') {
      const callback = this.ackCallbacks.get(msg.id);
      if (callback) {
        this.ackCallbacks.delete(msg.id);
        try {
          await callback();
        } catch (error) {
          Sentry.captureException(error);
        }
      }
      return;
    }

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

  private getWaMethodHandlers(): Record<
    string,
    (data: Record<string, unknown>) => Promise<Record<string, unknown>>
  > {
    return {
      group_metadata: async (d) => {
        const metadata = await this.whatsapp!.groupMetadata(d.jid as string);
        return metadata as unknown as Record<string, unknown>;
      },
      group_participants_update: async (d) => {
        const results = await this.whatsapp!.groupParticipantsUpdate(
          d.jid as string,
          d.participants as string[],
          d.action as 'add' | 'remove' | 'promote' | 'demote',
        );
        return { results };
      },
      on_whatsapp: async (d) => {
        const results = await this.whatsapp!.onWhatsApp(...(d.jids as string[]));
        return { results };
      },
      send_message: async (d) => {
        const result = await this.whatsapp!.sendMessage(
          d.jid as string,
          d.content as AnyMessageContent,
          d.options as Record<string, unknown> | undefined,
        );
        return (result ?? {}) as Record<string, unknown>;
      },
      group_update_subject: async (d) => {
        await this.whatsapp!.groupUpdateSubject(d.jid as string, d.subject as string);
        return {};
      },
      group_update_description: async (d) => {
        await this.whatsapp!.groupUpdateDescription(d.jid as string, d.description as string);
        return {};
      },
      send_presence_update: async (d) => {
        await this.whatsapp!.sendPresenceUpdate(
          d.type as 'available' | 'composing' | 'recording' | 'paused' | 'unavailable',
          d.jid as string,
        );
        return {};
      },
      download_media: async (d) => {
        if (!this.mediaHandler) throw new Error('MediaHandler not available');
        const messageId = d.message_id as string;
        const stored = this.messageStore.get(messageId);
        if (!stored) throw new Error(`Message ${messageId} not found in store`);
        const buffer = await this.mediaHandler.downloadMedia(stored, d.source as string);
        return { buffer: buffer.toString('base64') };
      },
      update_profile_picture: async (d) => {
        const imgBuffer = Buffer.from(d.image as string, 'base64');
        await this.whatsapp!.updateProfilePicture(d.jid as string, imgBuffer);
        return {};
      },
    };
  }

  private async executeWaMethod(
    method: string,
    data: Record<string, unknown>,
  ): Promise<Record<string, unknown>> {
    if (!this.whatsapp) throw new Error('WhatsApp not available');
    const handler = this.getWaMethodHandlers()[method];
    if (!handler) throw new Error(`Unknown wa_call method: ${method}`);
    return handler(data);
  }

  private getContentDeserializers(
    buffers: Buffer[],
    idx: { value: number },
  ): Record<
    string,
    (
      cd: Record<string, unknown>,
      caption: string | undefined,
    ) => AnyMessageContent | Promise<AnyMessageContent>
  > {
    const takeBuffer = (): Buffer => {
      const buf = buffers[idx.value++];
      if (!buf || buf.length === 0) {
        throw new Error(
          `Missing binary frame at index ${idx.value - 1} (received ${buffers.length} frames)`,
        );
      }
      return buf;
    };

    return {
      text: (cd) =>
        cd.mentions
          ? { text: cd.text as string, mentions: cd.mentions as string[] }
          : { text: cd.text as string },
      image: (cd, cap) => ({
        image: { url: cd.url as string },
        viewOnce: cd.view_once as boolean,
        caption: cap,
      }),
      image_buffer: (cd, cap) => ({
        image: takeBuffer(),
        viewOnce: cd.view_once as boolean,
        caption: cap,
      }),
      video: (cd, cap) => ({
        video: { url: cd.url as string },
        viewOnce: cd.view_once as boolean,
        caption: cap,
      }),
      video_buffer: (cd, cap) => ({
        video: takeBuffer(),
        viewOnce: cd.view_once as boolean,
        gifPlayback: (cd.gif_playback as boolean) ?? false,
        caption: cap,
      }),
      audio: (cd) => ({
        audio: { url: cd.url as string },
        viewOnce: cd.view_once as boolean,
        mimetype: (cd.mimetype as string) ?? 'audio/mp4',
      }),
      audio_buffer: (cd) => ({
        audio: takeBuffer(),
        mimetype: (cd.mimetype as string) ?? 'audio/mp4',
      }),
      sticker: async (cd) => {
        const buf = takeBuffer();
        const pack = (cd.pack as string) ?? '';
        const author = (cd.author as string) ?? '';
        if (pack || author) {
          const injected = await injectStickerExif(buf, pack, author);
          return { sticker: injected };
        }
        return { sticker: buf };
      },
      raw: (cd) => cd.content as AnyMessageContent,
    };
  }

  private async deserializeMessages(requestId: string, response: WSMessage): Promise<Message[]> {
    const msgs = (response.data?.messages as Array<Record<string, unknown>>) ?? [];
    const buffers = this.pendingBinary.get(requestId) ?? [];
    this.pendingBinary.delete(requestId);

    const idx = { value: 0 };
    const deserializers = this.getContentDeserializers(buffers, idx);

    return Promise.all(
      msgs.map(async (m) => {
        const cd = m.content as Record<string, unknown>;
        const contentType = cd.type as string;
        const caption = cd.caption as string | undefined;

        const deserializer = deserializers[contentType];
        const content: AnyMessageContent = deserializer
          ? await deserializer(cd, caption)
          : { text: `Unknown content type: ${contentType}` };

        const message: Message = { jid: m.jid as string, content };

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
      }),
    );
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
    this.ackCallbacks.clear();
  }
}
