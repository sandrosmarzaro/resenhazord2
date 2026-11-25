import { describe, it, expect, vi } from 'vitest';

import ReplyDeserializer from '../../../src/bridge/ReplyDeserializer.js';

vi.mock('../../../src/utils/StickerExif.js', () => ({
  default: vi.fn().mockResolvedValue(Buffer.from('exif-sticker')),
}));

function content(c: Record<string, unknown>): Record<string, unknown> {
  return { jid: 'g@g.us', content: c };
}

describe('ReplyDeserializer', () => {
  describe('text', () => {
    it('plain text', async () => {
      const message = await ReplyDeserializer.toMessage(content({ type: 'text', text: 'oi' }));
      expect(message.content).toEqual({ text: 'oi' });
    });

    it('text with mentions', async () => {
      const message = await ReplyDeserializer.toMessage(
        content({ type: 'text', text: 'oi', mentions: ['u@s'] }),
      );
      expect(message.content).toEqual({ text: 'oi', mentions: ['u@s'] });
    });
  });

  describe('url-backed media', () => {
    it('image', async () => {
      const message = await ReplyDeserializer.toMessage(
        content({ type: 'image', url: 'https://x/i.jpg', view_once: true, caption: 'c' }),
      );
      expect(message.content).toEqual({
        image: { url: 'https://x/i.jpg' },
        viewOnce: true,
        caption: 'c',
      });
    });

    it('video', async () => {
      const message = await ReplyDeserializer.toMessage(
        content({ type: 'video', url: 'https://x/v.mp4', view_once: false }),
      );
      expect(message.content).toMatchObject({ video: { url: 'https://x/v.mp4' }, viewOnce: false });
    });

    it('video with jpeg_thumbnail carries it as jpegThumbnail', async () => {
      const message = await ReplyDeserializer.toMessage(
        content({ type: 'video', url: 'https://x/v.mp4', jpeg_thumbnail: 'dGh1bWI=' }),
      );
      expect(message.content).toMatchObject({ jpegThumbnail: 'dGh1bWI=' });
    });

    it('video without jpeg_thumbnail leaves the key out', async () => {
      const message = await ReplyDeserializer.toMessage(
        content({ type: 'video', url: 'https://x/v.mp4' }),
      );
      expect(message.content).not.toHaveProperty('jpegThumbnail');
    });

    it('audio with default mimetype', async () => {
      const message = await ReplyDeserializer.toMessage(
        content({ type: 'audio', url: 'https://x/a' }),
      );
      expect(message.content).toMatchObject({
        audio: { url: 'https://x/a' },
        mimetype: 'audio/mp4',
      });
    });
  });

  describe('buffer-backed media', () => {
    const b64 = Buffer.from([1, 2, 3]).toString('base64');

    it('video_buffer with gif playback', async () => {
      const message = await ReplyDeserializer.toMessage(
        content({ type: 'video_buffer', buffer_b64: b64, gif_playback: true }),
      );
      expect(message.content).toMatchObject({ video: Buffer.from([1, 2, 3]), gifPlayback: true });
    });

    it('video_buffer honors view_once', async () => {
      const message = await ReplyDeserializer.toMessage(
        content({ type: 'video_buffer', buffer_b64: b64, view_once: true }),
      );
      expect(message.content).toMatchObject({ video: Buffer.from([1, 2, 3]), viewOnce: true });
    });

    it('video_buffer with mentions', async () => {
      const message = await ReplyDeserializer.toMessage(
        content({ type: 'video_buffer', buffer_b64: b64, mentions: ['a@s', 'b@s'] }),
      );
      expect(message.content).toMatchObject({ mentions: ['a@s', 'b@s'] });
    });

    it('video_buffer without mentions leaves the key out', async () => {
      const message = await ReplyDeserializer.toMessage(
        content({ type: 'video_buffer', buffer_b64: b64 }),
      );
      expect(message.content).not.toHaveProperty('mentions');
    });

    it('video_buffer with jpeg_thumbnail carries it as jpegThumbnail', async () => {
      const message = await ReplyDeserializer.toMessage(
        content({ type: 'video_buffer', buffer_b64: b64, jpeg_thumbnail: 'dGh1bWI=' }),
      );
      expect(message.content).toMatchObject({ jpegThumbnail: 'dGh1bWI=' });
    });

    it('video_buffer without jpeg_thumbnail leaves the key out', async () => {
      const message = await ReplyDeserializer.toMessage(
        content({ type: 'video_buffer', buffer_b64: b64 }),
      );
      expect(message.content).not.toHaveProperty('jpegThumbnail');
    });

    it('audio_buffer', async () => {
      const message = await ReplyDeserializer.toMessage(
        content({ type: 'audio_buffer', buffer_b64: b64, mimetype: 'audio/ogg' }),
      );
      expect(message.content).toMatchObject({
        audio: Buffer.from([1, 2, 3]),
        mimetype: 'audio/ogg',
      });
    });

    it('sticker without exif', async () => {
      const message = await ReplyDeserializer.toMessage(
        content({ type: 'sticker', buffer_b64: b64 }),
      );
      expect(message.content).toEqual({ sticker: Buffer.from([1, 2, 3]) });
    });

    it('sticker with pack injects exif', async () => {
      const message = await ReplyDeserializer.toMessage(
        content({ type: 'sticker', buffer_b64: b64, pack: 'P', author: 'A' }),
      );
      expect(message.content).toEqual({ sticker: Buffer.from('exif-sticker') });
    });

    it('sticker with audio carries both buffers for the audio sticker send', async () => {
      const audio = Buffer.from('ogg').toString('base64');

      const message = await ReplyDeserializer.toMessage(
        content({ type: 'sticker', buffer_b64: b64, pack: 'P', audio_b64: audio }),
      );

      expect(message.audioSticker).toEqual({
        sticker: Buffer.from('exif-sticker'),
        audio: Buffer.from('ogg'),
      });
    });

    it('silent sticker has no audio sticker', async () => {
      const message = await ReplyDeserializer.toMessage(
        content({ type: 'sticker', buffer_b64: b64 }),
      );

      expect(message.audioSticker).toBeUndefined();
    });
  });

  describe('raw and unknown', () => {
    it('raw passes content through', async () => {
      const message = await ReplyDeserializer.toMessage(
        content({ type: 'raw', content: { poll: { name: 'q' } } }),
      );
      expect(message.content).toEqual({ poll: { name: 'q' } });
    });

    it('unknown type falls back to a text notice', async () => {
      const message = await ReplyDeserializer.toMessage(content({ type: 'mystery' }));
      expect(message.content).toEqual({ text: 'Unknown content type: mystery' });
    });
  });

  describe('options', () => {
    it('no options when none present', async () => {
      const message = await ReplyDeserializer.toMessage(content({ type: 'text', text: 'x' }));
      expect(message.options).toBeUndefined();
    });

    it('expiration only; quoting is the consumer responsibility', async () => {
      const message = await ReplyDeserializer.toMessage({
        jid: 'g@g.us',
        content: { type: 'text', text: 'x' },
        quoted_message_id: 'ORIG',
        expiration: 60,
      });
      expect(message.options).toEqual({ ephemeralExpiration: 60 });
    });
  });
});
