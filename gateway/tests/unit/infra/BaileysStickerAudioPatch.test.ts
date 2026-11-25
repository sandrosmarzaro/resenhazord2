import { describe, it, expect } from 'vitest';
import { normalizeMessageContent, proto } from '@whiskeysockets/baileys';
import protobuf from 'protobufjs';

// Guards the bun patch for WhatsApp audio stickers (proto 2.3000.105x, via whatsmeow).
// WhatsApp sends them as Message.audioStickerMessage (field 134, a FutureProofMessage)
// around a StickerMessage carrying audioMessage (field 26). Baileys' static protobuf
// code drops unknown fields, so without the patch the whole sticker decodes to nothing.
// Re-verify this when bumping @whiskeysockets/baileys.
describe('Baileys sticker audio patch', () => {
  const AUDIO_FIELD = 26;
  const STICKER_FIELD = 26;
  const AUDIO_STICKER_FIELD = 134;
  const FUTURE_PROOF_MESSAGE_FIELD = 1;
  const LENGTH_DELIMITED = 2;
  const audio = { url: 'https://mmg.whatsapp.net/audio', mimetype: 'audio/ogg; codecs=opus' };

  function field(number: number, bytes: Uint8Array): Uint8Array {
    return protobuf.Writer.create()
      .uint32((number << 3) | LENGTH_DELIMITED)
      .bytes(bytes)
      .finish();
  }

  function stickerWire(): Uint8Array {
    const audioBytes = proto.Message.AudioMessage.encode(audio).finish();
    const sticker = protobuf.Writer.create()
      .uint32(10)
      .string('https://mmg.whatsapp.net/sticker')
      .uint32((AUDIO_FIELD << 3) | LENGTH_DELIMITED)
      .bytes(audioBytes)
      .finish();
    return field(STICKER_FIELD, sticker);
  }

  function audioStickerWire(): Uint8Array {
    return field(AUDIO_STICKER_FIELD, field(FUTURE_PROOF_MESSAGE_FIELD, stickerWire()));
  }

  const message = {
    stickerMessage: { url: 'https://mmg.whatsapp.net/sticker', audioMessage: audio },
  };

  describe('sticker audio field', () => {
    it('decodes the nested audio from the wire', () => {
      const decoded = proto.Message.decode(stickerWire());

      expect(decoded.stickerMessage?.audioMessage).toMatchObject(audio);
    });

    it('encodes the nested audio to the wire', () => {
      const encoded = proto.Message.encode(message).finish();

      expect(Buffer.from(encoded)).toEqual(Buffer.from(stickerWire()));
    });

    it('keeps the nested audio through fromObject and toObject', () => {
      const roundTrip = proto.Message.toObject(proto.Message.fromObject(message));

      expect(roundTrip.stickerMessage?.audioMessage).toMatchObject(audio);
    });
  });

  describe('audio sticker wrapper', () => {
    it('decodes the wrapper from the wire', () => {
      const decoded = proto.Message.decode(audioStickerWire());

      expect(decoded.audioStickerMessage?.message?.stickerMessage?.audioMessage).toMatchObject(
        audio,
      );
    });

    it('encodes the wrapper to the wire', () => {
      const encoded = proto.Message.encode({ audioStickerMessage: { message } }).finish();

      expect(Buffer.from(encoded)).toEqual(Buffer.from(audioStickerWire()));
    });

    it('keeps the wrapper through fromObject and toObject', () => {
      const wrapped = { audioStickerMessage: { message } };

      const roundTrip = proto.Message.toObject(proto.Message.fromObject(wrapped));

      expect(roundTrip.audioStickerMessage?.message?.stickerMessage?.audioMessage).toMatchObject(
        audio,
      );
    });

    it('is unwrapped by normalizeMessageContent', () => {
      const decoded = proto.Message.decode(audioStickerWire());

      const content = normalizeMessageContent(decoded);

      expect(content?.stickerMessage?.audioMessage).toMatchObject(audio);
    });
  });
});
