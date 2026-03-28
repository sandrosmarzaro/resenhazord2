import PythonBridge from '../../../src/bridge/PythonBridge.js';
import { createMockWhatsAppPort } from '../../fixtures/factories/MockWhatsAppPort.js';
import { GroupCommandData } from '../../fixtures/index.js';
import type WhatsAppPort from '../../../src/ports/WhatsAppPort.js';

// --- Mock WebSocket ---

type WsEventHandler = (...args: unknown[]) => void;

class MockWebSocket {
  static readonly OPEN = 1;
  static readonly CONNECTING = 0;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;

  readyState = MockWebSocket.OPEN;
  binaryType = 'blob';
  send = vi.fn();
  close = vi.fn(() => {
    this.readyState = MockWebSocket.CLOSED;
  });

  private readonly handlers = new Map<string, WsEventHandler[]>();

  addEventListener(event: string, handler: WsEventHandler): void {
    if (!this.handlers.has(event)) this.handlers.set(event, []);
    this.handlers.get(event)!.push(handler);
  }

  emit(event: string, data?: unknown): void {
    for (const handler of this.handlers.get(event) ?? []) {
      handler(data);
    }
  }
}

// --- Helpers ---

let mockWs: MockWebSocket;
let wsCreationCount: number;

function onWsCreated(ws: MockWebSocket): void {
  mockWs = ws;
  wsCreationCount++;
}

class TestWebSocket extends MockWebSocket {
  constructor(_url: string) {
    super();
    onWsCreated(this);
  }
}

function stubWebSocket(): void {
  wsCreationCount = 0;
  vi.stubGlobal('WebSocket', TestWebSocket);
}

function createConnectedBridge(whatsapp?: WhatsAppPort): PythonBridge {
  const bridge = new PythonBridge('ws://test:8000/ws');
  if (whatsapp) bridge.setWhatsApp(whatsapp);
  bridge.connect();
  mockWs.emit('open');
  return bridge;
}

function lastSentJson(): Record<string, unknown> {
  const calls = mockWs.send.mock.calls;
  const last = [...calls].reverse().find((c) => typeof c[0] === 'string');
  return JSON.parse(last![0] as string);
}

function simulateJsonMessage(msg: Record<string, unknown>): void {
  mockWs.emit('message', { data: JSON.stringify(msg) });
}

function simulateBinaryMessage(buffer: Buffer): void {
  mockWs.emit('message', { data: buffer });
}

function simulateArrayBufferMessage(data: Uint8Array): void {
  mockWs.emit('message', { data: data.buffer });
}

async function flushAsync(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 0));
}

// --- Setup ---

beforeEach(() => {
  stubWebSocket();
});

afterEach(() => {
  vi.restoreAllMocks();
});

// --- Tests ---

describe('PythonBridge', () => {
  describe('connection', () => {
    it('creates WebSocket on connect', () => {
      const bridge = new PythonBridge('ws://custom:9000/ws');
      bridge.connect();

      expect(mockWs).toBeDefined();
      expect(bridge.isConnected).toBe(true);
    });

    it('isConnected returns true when open', () => {
      const bridge = createConnectedBridge();

      expect(bridge.isConnected).toBe(true);
    });

    it('isConnected returns false before connect', () => {
      const bridge = new PythonBridge('ws://test:8000/ws');

      expect(bridge.isConnected).toBe(false);
    });

    it('does not create duplicate connections', () => {
      const bridge = new PythonBridge('ws://test:8000/ws');
      bridge.connect();
      bridge.connect();

      expect(wsCreationCount).toBe(1);
    });

    it('closes WebSocket on disconnect', () => {
      const bridge = createConnectedBridge();
      bridge.disconnect();

      expect(mockWs.close).toHaveBeenCalled();
      expect(bridge.isConnected).toBe(false);
    });

    it('rejects pending requests on close', async () => {
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',test' });

      const promise = bridge.sendCommand(data);
      mockWs.emit('close');

      await expect(promise).rejects.toThrow('WebSocket closed');
    });

    it('does not reconnect after explicit disconnect', () => {
      vi.useFakeTimers();
      const bridge = createConnectedBridge();
      bridge.disconnect();

      vi.advanceTimersByTime(60000);

      expect(wsCreationCount).toBe(1);
      vi.useRealTimers();
    });

    it('schedules reconnect on close', () => {
      vi.useFakeTimers();
      const bridge = new PythonBridge('ws://test:8000/ws');
      bridge.connect();
      mockWs.emit('open');

      mockWs.emit('close');
      vi.advanceTimersByTime(1000);

      expect(wsCreationCount).toBe(2);
      vi.useRealTimers();
    });

    it('resets reconnect delay on successful connection', () => {
      vi.useFakeTimers();
      const bridge = new PythonBridge('ws://test:8000/ws');
      bridge.connect();
      mockWs.emit('open');

      // First close: delay is 1000ms
      mockWs.emit('close');
      vi.advanceTimersByTime(1000);
      expect(wsCreationCount).toBe(2);

      // New connection opens, delay resets to 1000
      mockWs.emit('open');
      mockWs.emit('close');
      vi.advanceTimersByTime(1000);
      expect(wsCreationCount).toBe(3);

      vi.useRealTimers();
    });
  });

  describe('sendCommand', () => {
    it('returns null when not connected', async () => {
      const bridge = new PythonBridge('ws://test:8000/ws');
      const data = GroupCommandData.build({ text: ',test' });

      expect(await bridge.sendCommand(data)).toBeNull();
    });

    it('serializes command data correctly', async () => {
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',echo hello' });

      const promise = bridge.sendCommand(data);
      const sent = lastSentJson();

      expect(sent.type).toBe('command');
      const sentData = sent.data as Record<string, unknown>;
      expect(sentData.text).toBe(',echo hello');
      expect(sentData.jid).toBe(data.key.remoteJid);
      expect(sentData.sender_jid).toBe(data.key.participant);
      expect(sentData.is_group).toBe(true);
      expect(sentData.push_name).toBe(data.pushName);
      expect(sentData.message_id).toBe(data.key.id);
      expect(sentData.media_type).toBeNull();
      expect(sentData.media_buffer_size).toBe(0);

      simulateJsonMessage({ id: sent.id, type: 'no_match' });
      await promise;
    });

    it('returns null on no_match response', async () => {
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',unknown' });

      const promise = bridge.sendCommand(data);
      const sent = lastSentJson();
      simulateJsonMessage({ id: sent.id, type: 'no_match' });

      expect(await promise).toBeNull();
    });

    it('throws on error response', async () => {
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',test' });

      const promise = bridge.sendCommand(data);
      const sent = lastSentJson();
      simulateJsonMessage({
        id: sent.id,
        type: 'error',
        data: { message: 'Command failed' },
      });

      await expect(promise).rejects.toThrow('Command failed');
    });

    it('throws with default message when error has no message', async () => {
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',test' });

      const promise = bridge.sendCommand(data);
      const sent = lastSentJson();
      simulateJsonMessage({ id: sent.id, type: 'error', data: {} });

      await expect(promise).rejects.toThrow('Python command failed');
    });

    it('returns null for unexpected response type', async () => {
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',test' });

      const promise = bridge.sendCommand(data);
      const sent = lastSentJson();
      simulateJsonMessage({ id: sent.id, type: 'something_else' });

      expect(await promise).toBeNull();
    });

    it('invokes onAck callback when command_ack is received', async () => {
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',test' });
      const onAck = vi.fn();

      const promise = bridge.sendCommand(data, onAck);
      const sent = lastSentJson();

      simulateJsonMessage({ id: sent.id, type: 'command_ack' });
      await flushAsync();

      expect(onAck).toHaveBeenCalledOnce();

      simulateJsonMessage({
        id: sent.id,
        type: 'command_response',
        data: { messages: [{ jid: 'g@g.us', content: { type: 'text', text: 'ok' } }] },
      });

      const result = await promise;
      expect(result).toHaveLength(1);
    });

    it('does not invoke onAck when no command_ack is received', async () => {
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',unknown' });
      const onAck = vi.fn();

      const promise = bridge.sendCommand(data, onAck);
      const sent = lastSentJson();

      simulateJsonMessage({ id: sent.id, type: 'no_match' });

      await promise;
      expect(onAck).not.toHaveBeenCalled();
    });

    it('times out after configured duration', async () => {
      vi.useFakeTimers();
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',test' });

      const promise = bridge.sendCommand(data);
      vi.advanceTimersByTime(60000);

      await expect(promise).rejects.toThrow('timeout');
      vi.useRealTimers();
    });
  });

  describe('deserializeMessages', () => {
    it('deserializes text content', async () => {
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',test' });

      const promise = bridge.sendCommand(data);
      const sent = lastSentJson();
      simulateJsonMessage({
        id: sent.id,
        type: 'command_response',
        data: {
          messages: [{ jid: 'group@g.us', content: { type: 'text', text: 'Hello world' } }],
        },
      });

      const result = await promise;
      expect(result).toHaveLength(1);
      expect(result![0].jid).toBe('group@g.us');
      expect(result![0].content).toEqual({ text: 'Hello world' });
    });

    it('deserializes text with mentions', async () => {
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',test' });

      const promise = bridge.sendCommand(data);
      const sent = lastSentJson();
      simulateJsonMessage({
        id: sent.id,
        type: 'command_response',
        data: {
          messages: [
            {
              jid: 'group@g.us',
              content: {
                type: 'text',
                text: '@user hello',
                mentions: ['5511999@s.whatsapp.net'],
              },
            },
          ],
        },
      });

      const result = await promise;
      expect(result![0].content).toEqual({
        text: '@user hello',
        mentions: ['5511999@s.whatsapp.net'],
      });
    });

    it('deserializes image from URL', async () => {
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',test' });

      const promise = bridge.sendCommand(data);
      const sent = lastSentJson();
      simulateJsonMessage({
        id: sent.id,
        type: 'command_response',
        data: {
          messages: [
            {
              jid: 'group@g.us',
              content: {
                type: 'image',
                url: 'https://example.com/img.jpg',
                view_once: false,
                caption: 'A picture',
              },
            },
          ],
        },
      });

      const result = await promise;
      expect(result![0].content).toEqual({
        image: { url: 'https://example.com/img.jpg' },
        viewOnce: false,
        caption: 'A picture',
      });
    });

    it('deserializes video from URL', async () => {
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',test' });

      const promise = bridge.sendCommand(data);
      const sent = lastSentJson();
      simulateJsonMessage({
        id: sent.id,
        type: 'command_response',
        data: {
          messages: [
            {
              jid: 'group@g.us',
              content: {
                type: 'video',
                url: 'https://example.com/video.mp4',
                view_once: false,
                caption: 'A video',
              },
            },
          ],
        },
      });

      const result = await promise;
      expect(result![0].content).toEqual({
        video: { url: 'https://example.com/video.mp4' },
        viewOnce: false,
        caption: 'A video',
      });
    });

    it('deserializes audio from URL', async () => {
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',test' });

      const promise = bridge.sendCommand(data);
      const sent = lastSentJson();
      simulateJsonMessage({
        id: sent.id,
        type: 'command_response',
        data: {
          messages: [
            {
              jid: 'group@g.us',
              content: {
                type: 'audio',
                url: 'https://example.com/audio.mp3',
                view_once: false,
                mimetype: 'audio/mpeg',
              },
            },
          ],
        },
      });

      const result = await promise;
      expect(result![0].content).toEqual({
        audio: { url: 'https://example.com/audio.mp3' },
        viewOnce: false,
        mimetype: 'audio/mpeg',
      });
    });

    it('uses default mimetype for audio', async () => {
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',test' });

      const promise = bridge.sendCommand(data);
      const sent = lastSentJson();
      simulateJsonMessage({
        id: sent.id,
        type: 'command_response',
        data: {
          messages: [
            {
              jid: 'group@g.us',
              content: { type: 'audio', url: 'https://example.com/a.mp4', view_once: false },
            },
          ],
        },
      });

      const result = await promise;
      expect((result![0].content as Record<string, unknown>).mimetype).toBe('audio/mp4');
    });

    it('deserializes image from buffer', async () => {
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',test' });

      const promise = bridge.sendCommand(data);
      const sent = lastSentJson();

      const imgBuffer = Buffer.from([0x89, 0x50, 0x4e, 0x47]);
      simulateBinaryMessage(imgBuffer);
      simulateJsonMessage({
        id: sent.id,
        type: 'command_response',
        data: {
          messages: [
            {
              jid: 'group@g.us',
              content: { type: 'image_buffer', view_once: false, caption: 'From buffer' },
            },
          ],
        },
      });

      const result = await promise;
      const content = result![0].content as Record<string, unknown>;
      expect(content.caption).toBe('From buffer');
      expect(Buffer.isBuffer(content.image)).toBe(true);
    });

    it('deserializes video from buffer with gif playback', async () => {
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',test' });

      const promise = bridge.sendCommand(data);
      const sent = lastSentJson();

      simulateBinaryMessage(Buffer.from('video-data'));
      simulateJsonMessage({
        id: sent.id,
        type: 'command_response',
        data: {
          messages: [
            {
              jid: 'group@g.us',
              content: {
                type: 'video_buffer',
                view_once: false,
                gif_playback: true,
                caption: 'GIF',
              },
            },
          ],
        },
      });

      const result = await promise;
      const content = result![0].content as Record<string, unknown>;
      expect(content.gifPlayback).toBe(true);
      expect(content.caption).toBe('GIF');
      expect(Buffer.isBuffer(content.video)).toBe(true);
    });

    it('deserializes audio from buffer', async () => {
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',test' });

      const promise = bridge.sendCommand(data);
      const sent = lastSentJson();

      simulateBinaryMessage(Buffer.from('audio-data'));
      simulateJsonMessage({
        id: sent.id,
        type: 'command_response',
        data: {
          messages: [
            {
              jid: 'group@g.us',
              content: { type: 'audio_buffer', mimetype: 'audio/ogg' },
            },
          ],
        },
      });

      const result = await promise;
      const content = result![0].content as Record<string, unknown>;
      expect(content.mimetype).toBe('audio/ogg');
      expect(Buffer.isBuffer(content.audio)).toBe(true);
    });

    it('deserializes sticker from buffer', async () => {
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',test' });

      const promise = bridge.sendCommand(data);
      const sent = lastSentJson();

      simulateBinaryMessage(Buffer.from('sticker-data'));
      simulateJsonMessage({
        id: sent.id,
        type: 'command_response',
        data: {
          messages: [{ jid: 'group@g.us', content: { type: 'sticker' } }],
        },
      });

      const result = await promise;
      const content = result![0].content as Record<string, unknown>;
      expect(Buffer.isBuffer(content.sticker)).toBe(true);
    });

    it('deserializes raw content', async () => {
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',test' });

      const promise = bridge.sendCommand(data);
      const sent = lastSentJson();
      simulateJsonMessage({
        id: sent.id,
        type: 'command_response',
        data: {
          messages: [
            {
              jid: 'group@g.us',
              content: { type: 'raw', content: { text: 'raw content' } },
            },
          ],
        },
      });

      const result = await promise;
      expect(result![0].content).toEqual({ text: 'raw content' });
    });

    it('handles unknown content type', async () => {
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',test' });

      const promise = bridge.sendCommand(data);
      const sent = lastSentJson();
      simulateJsonMessage({
        id: sent.id,
        type: 'command_response',
        data: {
          messages: [{ jid: 'group@g.us', content: { type: 'alien_format' } }],
        },
      });

      const result = await promise;
      expect(result![0].content).toEqual({ text: 'Unknown content type: alien_format' });
    });

    it('adds quoted message options', async () => {
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',test' });

      const promise = bridge.sendCommand(data);
      const sent = lastSentJson();
      simulateJsonMessage({
        id: sent.id,
        type: 'command_response',
        data: {
          messages: [
            {
              jid: 'group@g.us',
              content: { type: 'text', text: 'reply' },
              quoted_message_id: 'MSG_123',
            },
          ],
        },
      });

      const result = await promise;
      expect(result![0].options?.quoted).toEqual({ key: { id: 'MSG_123' } });
    });

    it('adds expiration options', async () => {
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',test' });

      const promise = bridge.sendCommand(data);
      const sent = lastSentJson();
      simulateJsonMessage({
        id: sent.id,
        type: 'command_response',
        data: {
          messages: [
            {
              jid: 'group@g.us',
              content: { type: 'text', text: 'reply' },
              expiration: 86400,
            },
          ],
        },
      });

      const result = await promise;
      expect(result![0].options?.ephemeralExpiration).toBe(86400);
    });

    it('deserializes multiple messages', async () => {
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',test' });

      const promise = bridge.sendCommand(data);
      const sent = lastSentJson();
      simulateJsonMessage({
        id: sent.id,
        type: 'command_response',
        data: {
          messages: [
            { jid: 'g@g.us', content: { type: 'text', text: 'first' } },
            { jid: 'g@g.us', content: { type: 'text', text: 'second' } },
          ],
        },
      });

      const result = await promise;
      expect(result).toHaveLength(2);
      expect((result![0].content as { text: string }).text).toBe('first');
      expect((result![1].content as { text: string }).text).toBe('second');
    });

    it('consumes multiple buffers in order', async () => {
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',test' });

      const promise = bridge.sendCommand(data);
      const sent = lastSentJson();

      simulateBinaryMessage(Buffer.from('image-bytes'));
      simulateBinaryMessage(Buffer.from('sticker-bytes'));
      simulateJsonMessage({
        id: sent.id,
        type: 'command_response',
        data: {
          messages: [
            {
              jid: 'g@g.us',
              content: { type: 'image_buffer', view_once: false },
            },
            {
              jid: 'g@g.us',
              content: { type: 'sticker' },
            },
          ],
        },
      });

      const result = await promise;
      const img = (result![0].content as Record<string, unknown>).image as Buffer;
      const sticker = (result![1].content as Record<string, unknown>).sticker as Buffer;
      expect(img.toString()).toBe('image-bytes');
      expect(sticker.toString()).toBe('sticker-bytes');
    });
  });

  describe('sendGroupEvent', () => {
    it('sends group event when connected', () => {
      const bridge = createConnectedBridge();
      bridge.sendGroupEvent({ type: 'join', jid: 'group@g.us' });

      const sent = lastSentJson();
      expect(sent.type).toBe('group_event');
      expect(sent.data).toEqual({ type: 'join', jid: 'group@g.us' });
    });

    it('does nothing when not connected', () => {
      const bridge = new PythonBridge('ws://test:8000/ws');
      bridge.sendGroupEvent({ type: 'join' });

      // No WebSocket created, so no send
    });
  });

  describe('handleWaCall', () => {
    it('delegates group_metadata to WhatsApp port', async () => {
      const mockWa = createMockWhatsAppPort({
        groupMetadata: vi.fn().mockResolvedValue({
          id: 'group@g.us',
          subject: 'Test Group',
          participants: [],
        }),
      });
      createConnectedBridge(mockWa);

      simulateJsonMessage({
        id: 'call-1',
        type: 'wa_call',
        method: 'group_metadata',
        data: { jid: 'group@g.us' },
      });

      await flushAsync();

      expect(mockWa.groupMetadata).toHaveBeenCalledWith('group@g.us');
      const response = findSentMessage('wa_result');
      expect(response.id).toBe('call-1');
      expect((response.data as Record<string, unknown>).subject).toBe('Test Group');
    });

    it('delegates send_message to WhatsApp port', async () => {
      const mockWa = createMockWhatsAppPort({
        sendMessage: vi.fn().mockResolvedValue({ key: { id: 'sent-1' } }),
      });
      createConnectedBridge(mockWa);

      simulateJsonMessage({
        id: 'call-2',
        type: 'wa_call',
        method: 'send_message',
        data: { jid: 'group@g.us', content: { text: 'hello' } },
      });

      await flushAsync();

      expect(mockWa.sendMessage).toHaveBeenCalledWith('group@g.us', { text: 'hello' }, undefined);
    });

    it('delegates group_participants_update to WhatsApp port', async () => {
      const mockWa = createMockWhatsAppPort({
        groupParticipantsUpdate: vi.fn().mockResolvedValue([{ status: 200 }]),
      });
      createConnectedBridge(mockWa);

      simulateJsonMessage({
        id: 'call-3',
        type: 'wa_call',
        method: 'group_participants_update',
        data: {
          jid: 'group@g.us',
          participants: ['user@s.whatsapp.net'],
          action: 'add',
        },
      });

      await flushAsync();

      expect(mockWa.groupParticipantsUpdate).toHaveBeenCalledWith(
        'group@g.us',
        ['user@s.whatsapp.net'],
        'add',
      );
    });

    it('delegates on_whatsapp to WhatsApp port', async () => {
      const mockWa = createMockWhatsAppPort({
        onWhatsApp: vi.fn().mockResolvedValue([{ exists: true, jid: '5511999@s.whatsapp.net' }]),
      });
      createConnectedBridge(mockWa);

      simulateJsonMessage({
        id: 'call-4',
        type: 'wa_call',
        method: 'on_whatsapp',
        data: { jids: ['5511999'] },
      });

      await flushAsync();

      expect(mockWa.onWhatsApp).toHaveBeenCalledWith('5511999');
    });

    it('delegates group_update_subject to WhatsApp port', async () => {
      const mockWa = createMockWhatsAppPort({
        groupUpdateSubject: vi.fn().mockResolvedValue(undefined),
      });
      createConnectedBridge(mockWa);

      simulateJsonMessage({
        id: 'call-5',
        type: 'wa_call',
        method: 'group_update_subject',
        data: { jid: 'group@g.us', subject: 'New Name' },
      });

      await flushAsync();

      expect(mockWa.groupUpdateSubject).toHaveBeenCalledWith('group@g.us', 'New Name');
      const response = findSentMessage('wa_result');
      expect(response.data).toEqual({});
    });

    it('delegates send_presence_update to WhatsApp port', async () => {
      const mockWa = createMockWhatsAppPort({
        sendPresenceUpdate: vi.fn().mockResolvedValue(undefined),
      });
      createConnectedBridge(mockWa);

      simulateJsonMessage({
        id: 'call-6',
        type: 'wa_call',
        method: 'send_presence_update',
        data: { type: 'composing', jid: 'group@g.us' },
      });

      await flushAsync();

      expect(mockWa.sendPresenceUpdate).toHaveBeenCalledWith('composing', 'group@g.us');
    });

    it('delegates update_profile_picture to WhatsApp port', async () => {
      const mockWa = createMockWhatsAppPort({
        updateProfilePicture: vi.fn().mockResolvedValue(undefined),
      });
      createConnectedBridge(mockWa);

      const base64Image = Buffer.from('fake-image').toString('base64');
      simulateJsonMessage({
        id: 'call-7',
        type: 'wa_call',
        method: 'update_profile_picture',
        data: { jid: 'group@g.us', image: base64Image },
      });

      await flushAsync();

      expect(mockWa.updateProfilePicture).toHaveBeenCalledWith('group@g.us', expect.any(Buffer));
    });

    it('sends error for unknown method', async () => {
      const mockWa = createMockWhatsAppPort();
      createConnectedBridge(mockWa);

      simulateJsonMessage({
        id: 'call-err-1',
        type: 'wa_call',
        method: 'nonexistent_method',
        data: {},
      });

      await flushAsync();

      const response = findSentMessage('error');
      expect(response.id).toBe('call-err-1');
      expect((response.data as Record<string, unknown>).code).toBe('WA_CALL_ERROR');
    });

    it('sends error when WhatsApp method throws', async () => {
      const mockWa = createMockWhatsAppPort({
        groupMetadata: vi.fn().mockRejectedValue(new Error('not found')),
      });
      createConnectedBridge(mockWa);

      simulateJsonMessage({
        id: 'call-err-2',
        type: 'wa_call',
        method: 'group_metadata',
        data: { jid: 'invalid@g.us' },
      });

      await flushAsync();

      const response = findSentMessage('error');
      expect(response.id).toBe('call-err-2');
      expect(response.data).toEqual(expect.objectContaining({ code: 'WA_CALL_ERROR' }));
    });

    it('ignores wa_call when WhatsApp not set', async () => {
      createConnectedBridge();

      simulateJsonMessage({
        id: 'call-ignored',
        type: 'wa_call',
        method: 'group_metadata',
        data: { jid: 'group@g.us' },
      });

      await flushAsync();

      const waResults = mockWs.send.mock.calls.filter(
        (c) => typeof c[0] === 'string' && c[0].includes('wa_result'),
      );
      expect(waResults).toHaveLength(0);
    });
  });

  describe('binary frame handling', () => {
    it('sets binaryType to arraybuffer on connect', () => {
      createConnectedBridge();

      expect(mockWs.binaryType).toBe('arraybuffer');
    });

    it('handles binary data received as ArrayBuffer', async () => {
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',test' });

      const promise = bridge.sendCommand(data);
      const sent = lastSentJson();

      const bytes = new Uint8Array([0x89, 0x50, 0x4e, 0x47]);
      simulateArrayBufferMessage(bytes);
      simulateJsonMessage({
        id: sent.id,
        type: 'command_response',
        data: {
          messages: [
            {
              jid: 'group@g.us',
              content: { type: 'image_buffer', view_once: false, caption: 'Test' },
            },
          ],
        },
      });

      const result = await promise;
      const content = result![0].content as Record<string, unknown>;
      expect(Buffer.isBuffer(content.image)).toBe(true);
      expect((content.image as Buffer).length).toBe(4);
      expect(content.caption).toBe('Test');
    });

    it('preserves buffer content through ArrayBuffer conversion', async () => {
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',test' });

      const promise = bridge.sendCommand(data);
      const sent = lastSentJson();

      const original = new Uint8Array([0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10]);
      simulateArrayBufferMessage(original);
      simulateJsonMessage({
        id: sent.id,
        type: 'command_response',
        data: {
          messages: [
            {
              jid: 'group@g.us',
              content: { type: 'image_buffer', view_once: true },
            },
          ],
        },
      });

      const result = await promise;
      const image = (result![0].content as Record<string, unknown>).image as Buffer;
      expect([...image]).toEqual([0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10]);
    });

    it('cleans up pendingBinary after no_match so next binary command works', async () => {
      const bridge = createConnectedBridge();

      // First command returns no_match
      const data1 = GroupCommandData.build({ text: ',unknown' });
      const promise1 = bridge.sendCommand(data1);
      const sent1 = lastSentJson();
      simulateJsonMessage({ id: sent1.id, type: 'no_match' });
      await promise1;

      // Second command returns a sticker with binary
      const data2 = GroupCommandData.build({ text: ',sticker' });
      const promise2 = bridge.sendCommand(data2);
      const sent2 = lastSentJson();

      simulateArrayBufferMessage(new Uint8Array([0x52, 0x49, 0x46, 0x46]));
      simulateJsonMessage({
        id: sent2.id,
        type: 'command_response',
        data: {
          messages: [{ jid: 'g@g.us', content: { type: 'sticker' } }],
        },
      });

      const result = await promise2;
      const sticker = (result![0].content as Record<string, unknown>).sticker as Buffer;
      expect([...sticker]).toEqual([0x52, 0x49, 0x46, 0x46]);
    });

    it('associates multiple ArrayBuffer frames with correct response', async () => {
      const bridge = createConnectedBridge();
      const data = GroupCommandData.build({ text: ',test' });

      const promise = bridge.sendCommand(data);
      const sent = lastSentJson();

      simulateArrayBufferMessage(new Uint8Array([1, 2, 3]));
      simulateArrayBufferMessage(new Uint8Array([4, 5, 6]));
      simulateJsonMessage({
        id: sent.id,
        type: 'command_response',
        data: {
          messages: [
            { jid: 'g@g.us', content: { type: 'image_buffer', view_once: false } },
            { jid: 'g@g.us', content: { type: 'sticker' } },
          ],
        },
      });

      const result = await promise;
      const img = (result![0].content as Record<string, unknown>).image as Buffer;
      const sticker = (result![1].content as Record<string, unknown>).sticker as Buffer;
      expect([...img]).toEqual([1, 2, 3]);
      expect([...sticker]).toEqual([4, 5, 6]);
    });
  });
});

// --- Helper to find sent messages by type ---

function findSentMessage(type: string): Record<string, unknown> {
  const calls = mockWs.send.mock.calls;
  const match = calls.find((c) => typeof c[0] === 'string' && c[0].includes(`"type":"${type}"`));
  if (!match) throw new Error(`No sent message with type "${type}" found`);
  return JSON.parse(match[0] as string);
}
