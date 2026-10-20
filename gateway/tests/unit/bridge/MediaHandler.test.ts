import { describe, it, expect, vi } from 'vitest';
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

    it('ignores a quoted view-once wrapper, which never carries media to linked devices', () => {
      const data = quoting({ viewOnceMessageV2: { message: { imageMessage: {} } } });

      expect(handler.detectMedia(data)).toBeNull();
    });
  });

  describe('downloadMedia', () => {
    it('downloads the quoted message content', async () => {
      const buffer = Buffer.from([1, 2, 3]);
      vi.mocked(downloadMediaMessage).mockResolvedValue(buffer);
      const stored = WAMessageFactory.build({}, { transient: { isGroup: true } });
      const quotedMessage = { imageMessage: { mimetype: 'image/jpeg' } };
      stored.message = {
        extendedTextMessage: { text: ',sticker', contextInfo: { quotedMessage } },
      };

      const result = await handler.downloadMedia(stored, 'quoted');

      expect(result).toBe(buffer);
      const [message] = vi.mocked(downloadMediaMessage).mock.calls[0];
      expect(message.message).toEqual(quotedMessage);
    });
  });
});
