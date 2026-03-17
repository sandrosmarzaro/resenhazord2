import { describe, it, expect } from 'vitest';
import type { WAMessage } from '@whiskeysockets/baileys';
import WaMessageFactory from '../../../src/factories/WaMessageFactory.js';

const baseKey = { remoteJid: '123@s.whatsapp.net', fromMe: false as const, id: 'test' };

describe('WaMessageFactory', () => {
  describe('getText()', () => {
    it('returns conversation text', () => {
      const msg: WAMessage = { key: baseKey, message: { conversation: 'hello' } };
      expect(WaMessageFactory.getText(msg)).toBe('hello');
    });

    it('returns extendedTextMessage text', () => {
      const msg: WAMessage = { key: baseKey, message: { extendedTextMessage: { text: 'hi' } } };
      expect(WaMessageFactory.getText(msg)).toBe('hi');
    });

    it('returns imageMessage caption', () => {
      const msg: WAMessage = {
        key: baseKey,
        message: { imageMessage: { caption: 'a photo' } },
      };
      expect(WaMessageFactory.getText(msg)).toBe('a photo');
    });

    it('returns videoMessage caption', () => {
      const msg: WAMessage = {
        key: baseKey,
        message: { videoMessage: { caption: 'a video' } },
      };
      expect(WaMessageFactory.getText(msg)).toBe('a video');
    });

    it('returns documentWithCaptionMessage caption', () => {
      const msg: WAMessage = {
        key: baseKey,
        message: {
          documentWithCaptionMessage: {
            message: { documentMessage: { caption: 'a doc' } },
          },
        },
      };
      expect(WaMessageFactory.getText(msg)).toBe('a doc');
    });

    it('returns empty string when message is null', () => {
      const msg: WAMessage = { key: baseKey, message: null };
      expect(WaMessageFactory.getText(msg)).toBe('');
    });

    it('returns empty string when no known type is present', () => {
      const msg: WAMessage = { key: baseKey, message: {} };
      expect(WaMessageFactory.getText(msg)).toBe('');
    });
  });

  describe('getExpiration()', () => {
    it('returns expiration from extendedTextMessage contextInfo', () => {
      const msg: WAMessage = {
        key: baseKey,
        message: { extendedTextMessage: { contextInfo: { expiration: 86400 } } },
      };
      expect(WaMessageFactory.getExpiration(msg)).toBe(86400);
    });

    it('returns expiration from imageMessage contextInfo', () => {
      const msg: WAMessage = {
        key: baseKey,
        message: { imageMessage: { contextInfo: { expiration: 3600 } } },
      };
      expect(WaMessageFactory.getExpiration(msg)).toBe(3600);
    });

    it('returns expiration from videoMessage contextInfo', () => {
      const msg: WAMessage = {
        key: baseKey,
        message: { videoMessage: { contextInfo: { expiration: 7200 } } },
      };
      expect(WaMessageFactory.getExpiration(msg)).toBe(7200);
    });

    it('returns expiration from documentWithCaptionMessage contextInfo', () => {
      const msg: WAMessage = {
        key: baseKey,
        message: {
          documentWithCaptionMessage: {
            message: { documentMessage: { contextInfo: { expiration: 1800 } } },
          },
        },
      };
      expect(WaMessageFactory.getExpiration(msg)).toBe(1800);
    });

    it('returns undefined when message is null', () => {
      const msg: WAMessage = { key: baseKey, message: null };
      expect(WaMessageFactory.getExpiration(msg)).toBeUndefined();
    });

    it('returns undefined when no expiration is set', () => {
      const msg: WAMessage = { key: baseKey, message: { conversation: 'hello' } };
      expect(WaMessageFactory.getExpiration(msg)).toBeUndefined();
    });
  });
});
