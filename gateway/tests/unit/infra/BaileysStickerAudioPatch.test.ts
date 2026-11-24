import { describe, it, expect } from 'vitest';
import { proto } from '@whiskeysockets/baileys';
import protobuf from 'protobufjs';

// Guards the bun patch that adds StickerMessage.audioMessage (field 26, from WhatsApp's
// 2.3000.105x proto via whatsmeow). Baileys' static protobuf code drops unknown fields,
// so without the patch an audio sticker decodes as a silent one and can't be sent.
// Re-verify this when bumping @whiskeysockets/baileys.
describe('Baileys sticker audio patch', () => {
  const AUDIO_FIELD = 26;
  const STICKER_FIELD = 26;
  const LENGTH_DELIMITED = 2;
  const audio = { url: 'https://mmg.whatsapp.net/audio', mimetype: 'audio/ogg; codecs=opus' };

  function wireBytes(): Uint8Array {
    const audioBytes = proto.Message.AudioMessage.encode(audio).finish();
    const sticker = protobuf.Writer.create()
      .uint32(10)
      .string('https://mmg.whatsapp.net/sticker')
      .uint32((AUDIO_FIELD << 3) | LENGTH_DELIMITED)
      .bytes(audioBytes)
      .finish();
    return protobuf.Writer.create()
      .uint32((STICKER_FIELD << 3) | LENGTH_DELIMITED)
      .bytes(sticker)
      .finish();
  }

  const message = {
    stickerMessage: { url: 'https://mmg.whatsapp.net/sticker', audioMessage: audio },
  };

  it('decodes the nested audio from the wire', () => {
    const decoded = proto.Message.decode(wireBytes());

    expect(decoded.stickerMessage?.audioMessage).toMatchObject(audio);
  });

  it('encodes the nested audio to the wire', () => {
    const encoded = proto.Message.encode(message).finish();

    expect(Buffer.from(encoded)).toEqual(Buffer.from(wireBytes()));
  });

  it('keeps the nested audio through fromObject and toObject', () => {
    const roundTrip = proto.Message.toObject(proto.Message.fromObject(message));

    expect(roundTrip.stickerMessage?.audioMessage).toMatchObject(audio);
  });
});
