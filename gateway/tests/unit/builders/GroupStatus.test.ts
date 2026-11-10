import { describe, it, expect } from 'vitest';
import { proto } from '@whiskeysockets/baileys';
import GroupStatus from '../../../src/builders/GroupStatus.js';
import UnsupportedGroupStatusError from '../../../src/builders/UnsupportedGroupStatusError.js';
import {
  TEXT_BACKGROUNDS,
  TEXT_FONTS,
  VOICE_BACKGROUNDS,
} from '../../../src/data/GroupStatusStyles.js';

const AUTHOR = '189129606340826@lid';
const Source = proto.ContextInfo.StatusSourceType;
const groupAttribution = {
  type: proto.StatusAttribution.Type.GROUP_STATUS,
  groupStatus: { authorJid: AUTHOR },
};

function innerOf(status: proto.IMessage): proto.IMessage {
  return status.groupStatusMessageV2!.message!;
}

describe('GroupStatus', () => {
  const first = () => 0;
  const last = () => 0.999;

  describe('media', () => {
    it('marks an image as a group status by the bot', () => {
      const status = new GroupStatus(AUTHOR, first).wrap({ imageMessage: { caption: 'oi' } });

      expect(innerOf(status)).toEqual({
        imageMessage: {
          caption: 'oi',
          contextInfo: {
            isGroupStatus: true,
            statusSourceType: Source.IMAGE,
            statusAttributions: [groupAttribution],
          },
        },
      });
    });

    it('marks a video with the video source', () => {
      const status = new GroupStatus(AUTHOR, first).wrap({ videoMessage: { seconds: 6 } });

      expect(innerOf(status).videoMessage!.contextInfo!.statusSourceType).toBe(Source.VIDEO);
    });

    it('keeps the context the content already carries', () => {
      const status = new GroupStatus(AUTHOR, first).wrap({
        imageMessage: { contextInfo: { mentionedJid: ['a@lid'] } },
      });

      expect(innerOf(status).imageMessage!.contextInfo!.mentionedJid).toEqual(['a@lid']);
    });
  });

  describe('voice', () => {
    it('sends audio as a voice note on a background, without attributions', () => {
      const status = new GroupStatus(AUTHOR, last).wrap({ audioMessage: { seconds: 5 } });

      expect(innerOf(status)).toEqual({
        audioMessage: {
          seconds: 5,
          ptt: true,
          backgroundArgb: VOICE_BACKGROUNDS.at(-1),
          contextInfo: { isGroupStatus: true, statusSourceType: Source.AUDIO },
        },
      });
    });
  });

  describe('text', () => {
    it('draws the background and the font from the style tables', () => {
      const status = new GroupStatus(AUTHOR, first).wrap({ extendedTextMessage: { text: 'oi' } });

      expect(innerOf(status)).toEqual({
        extendedTextMessage: {
          text: 'oi',
          textArgb: 0xffffffff,
          backgroundArgb: TEXT_BACKGROUNDS[0],
          font: TEXT_FONTS[0],
          contextInfo: {
            isGroupStatus: true,
            statusSourceType: Source.TEXT,
            statusAttributions: [groupAttribution],
          },
        },
      });
    });

    it('can draw the last style of each table', () => {
      const status = new GroupStatus(AUTHOR, last).wrap({ extendedTextMessage: { text: 'oi' } });
      const text = innerOf(status).extendedTextMessage!;

      expect([text.backgroundArgb, text.font]).toEqual([
        TEXT_BACKGROUNDS.at(-1),
        TEXT_FONTS.at(-1),
      ]);
    });
  });

  describe('message secret', () => {
    it('moves the content secret onto the wrapper', () => {
      const messageSecret = new Uint8Array(32).fill(7);

      const status = new GroupStatus(AUTHOR, first).wrap({
        messageContextInfo: { messageSecret },
        imageMessage: {},
      });

      expect(status.messageContextInfo).toEqual({ messageSecret });
      expect(innerOf(status).messageContextInfo).toBeUndefined();
    });

    it('creates a 32-byte secret when the content has none', () => {
      const status = new GroupStatus(AUTHOR, first).wrap({ imageMessage: {} });

      expect(status.messageContextInfo!.messageSecret).toHaveLength(32);
    });
  });

  describe('errors', () => {
    it('rejects content that cannot be a status', () => {
      const status = new GroupStatus(AUTHOR, first);
      const sticker = { stickerMessage: {} };

      expect(() => status.wrap(sticker)).toThrow(UnsupportedGroupStatusError);
    });
  });
});
