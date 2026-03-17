import { describe, it, expect } from 'vitest';
import Reply from '../../../src/builders/Reply.js';
import { GroupCommandData } from '../../fixtures/index.js';

describe('Reply', () => {
  const data = GroupCommandData.build({ text: ',test', expiration: 86400 });
  const jid = data.key.remoteJid!;

  describe('text()', () => {
    it('should build a text message', () => {
      const msg = Reply.to(data).text('hello');

      expect(msg.jid).toBe(jid);
      expect(msg.content).toEqual({ text: 'hello' });
      expect(msg.options?.quoted).toBe(data);
      expect(msg.options?.ephemeralExpiration).toBe(86400);
    });
  });

  describe('textWith()', () => {
    it('should build a text message with mentions', () => {
      const mentions = ['123@s.whatsapp.net'];
      const msg = Reply.to(data).textWith('hello @123', mentions);

      expect(msg.content).toEqual({ text: 'hello @123', mentions });
    });
  });

  describe('image()', () => {
    it('should build an image message with viewOnce', () => {
      const msg = Reply.to(data).image('https://example.com/img.jpg');

      expect(msg.content).toEqual({
        image: { url: 'https://example.com/img.jpg' },
        viewOnce: true,
      });
    });

    it('should include caption when provided', () => {
      const msg = Reply.to(data).image('https://example.com/img.jpg', 'caption');

      expect(msg.content).toEqual({
        image: { url: 'https://example.com/img.jpg' },
        viewOnce: true,
        caption: 'caption',
      });
    });
  });

  describe('imageBuffer()', () => {
    it('should build an image message from buffer with viewOnce', () => {
      const buffer = Buffer.from('fake-image');
      const msg = Reply.to(data).imageBuffer(buffer, 'cap');

      expect(msg.content).toEqual({
        image: buffer,
        viewOnce: true,
        caption: 'cap',
      });
    });
  });

  describe('video()', () => {
    it('should build a video message with viewOnce', () => {
      const msg = Reply.to(data).video('https://example.com/vid.mp4', 'vid');

      expect(msg.content).toEqual({
        video: { url: 'https://example.com/vid.mp4' },
        viewOnce: true,
        caption: 'vid',
      });
    });
  });

  describe('audio()', () => {
    it('should build an audio message with viewOnce and mimetype', () => {
      const msg = Reply.to(data).audio('https://example.com/audio.mp3');

      expect(msg.content).toEqual({
        audio: { url: 'https://example.com/audio.mp3' },
        viewOnce: true,
        mimetype: 'audio/mp4',
      });
    });
  });

  describe('sticker()', () => {
    it('should build a sticker message', () => {
      const buffer = Buffer.from('fake-sticker');
      const msg = Reply.to(data).sticker(buffer);

      expect(msg.content).toEqual({ sticker: buffer });
    });
  });

  describe('raw()', () => {
    it('should build a message with arbitrary content', () => {
      const content = { image: Buffer.from('x'), caption: 'raw' };
      const msg = Reply.to(data).raw(content);

      expect(msg.jid).toBe(jid);
      expect(msg.content).toBe(content);
      expect(msg.options?.quoted).toBe(data);
    });
  });

  describe('options', () => {
    it('should use undefined expiration when not set', () => {
      const noExpData = GroupCommandData.build({ text: ',test' });
      const msg = Reply.to(noExpData).text('hi');

      expect(msg.options?.ephemeralExpiration).toBeUndefined();
    });
  });
});
