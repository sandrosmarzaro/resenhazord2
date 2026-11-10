import { Readable } from 'node:stream';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { downloadMediaMessage } from '@whiskeysockets/baileys';

import MediaHandler from '../../../src/bridge/MediaHandler.js';
import { createMockWhatsAppPort } from '../../fixtures/factories/MockWhatsAppPort.js';
import { WAMessageFactory } from '../../fixtures/factories/WAMessageFactory.js';
import { GroupCommandData } from '../../fixtures/index.js';

vi.mock('@whiskeysockets/baileys', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@whiskeysockets/baileys')>()),
  downloadMediaMessage: vi.fn(),
}));

function quoting(quotedMessage: Record<string, unknown>) {
  const data = GroupCommandData.build({ text: ',sticker' });
  data.message = { extendedTextMessage: { text: ',sticker', contextInfo: { quotedMessage } } };
  return data;
}

describe('MediaHandler', () => {
  const handler = new MediaHandler(createMockWhatsAppPort());

  describe('detectMedia', () => {
    it('detects quoted media with its caption', () => {
      const data = quoting({ imageMessage: { caption: 'oi' } });

      expect(handler.detectMedia(data)).toEqual({
        type: 'image',
        source: 'quoted',
        caption: 'oi',
      });
    });

    it('reads a quoted document as the media its mimetype names', () => {
      const data = quoting({ documentMessage: { mimetype: 'video/mp4', caption: 'filme' } });

      expect(handler.detectMedia(data)).toEqual({
        type: 'video',
        source: 'quoted',
        caption: 'filme',
      });
    });

    it('unwraps a quoted document sent with a caption', () => {
      const data = quoting({
        documentWithCaptionMessage: { message: { documentMessage: { mimetype: 'audio/mpeg' } } },
      });

      expect(handler.detectMedia(data)).toEqual({ type: 'audio', source: 'quoted' });
    });

    it('ignores a quoted document that is not media', () => {
      const data = quoting({ documentMessage: { mimetype: 'application/pdf' } });

      expect(handler.detectMedia(data)).toBeNull();
    });

    it('ignores a quoted view-once wrapper, which never carries media to linked devices', () => {
      const data = quoting({ viewOnceMessageV2: { message: { imageMessage: {} } } });

      expect(handler.detectMedia(data)).toBeNull();
    });
  });

  describe('downloadMedia', () => {
    const quotedMessage = { imageMessage: { mimetype: 'image/jpeg' } };

    function storedQuoting() {
      const stored = WAMessageFactory.build({}, { transient: { isGroup: true } });
      stored.message = {
        extendedTextMessage: { text: ',sticker', contextInfo: { quotedMessage } },
      };
      return stored;
    }

    function downloading(stream: Readable) {
      // The stream overload of a function mocked as a whole; its type is the buffer one.
      vi.mocked(downloadMediaMessage).mockResolvedValue(stream as unknown as Buffer);
    }

    afterEach(() => {
      vi.useRealTimers();
    });

    it('downloads the quoted message content', async () => {
      downloading(Readable.from([Buffer.from([1, 2]), Buffer.from([3])]));

      const result = await handler.downloadMedia(storedQuoting(), 'quoted');

      expect(result).toEqual(Buffer.from([1, 2, 3]));
      const [message, type] = vi.mocked(downloadMediaMessage).mock.calls[0];
      expect([message.message, type]).toEqual([quotedMessage, 'stream']);
    });

    it('stops downloading media past the size cap', async () => {
      const mebibyte = Buffer.alloc(1024 * 1024);
      const stream = Readable.from(Array.from({ length: 65 }, () => mebibyte));
      downloading(stream);

      await expect(handler.downloadMedia(storedQuoting(), 'quoted')).rejects.toThrow(
        'Media is larger than 67108864 bytes',
      );
      expect(stream.destroyed).toBe(true);
    });

    it('stops a download that hangs', async () => {
      vi.useFakeTimers();
      const stream = new Readable({ read() {} });
      downloading(stream);

      const result = handler.downloadMedia(storedQuoting(), 'quoted');
      const rejected = expect(result).rejects.toThrow('Media download timed out');
      await vi.advanceTimersByTimeAsync(50_000);

      await rejected;
      expect(stream.destroyed).toBe(true);
    });
  });
});
