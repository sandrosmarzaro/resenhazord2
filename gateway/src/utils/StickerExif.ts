import { Image as WebPImage } from 'node-webpmux';

const EXIF_HEADER = Buffer.from([
  0x49, 0x49, 0x2a, 0x00, 0x08, 0x00, 0x00, 0x00, 0x01, 0x00, 0x41, 0x57, 0x07, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x16, 0x00, 0x00, 0x00,
]);

function buildExifPayload(pack: string, author: string): Buffer {
  const json = JSON.stringify({
    'sticker-pack-name': pack,
    'sticker-pack-publisher': author,
  });
  const jsonBuf = Buffer.from(json, 'utf-8');
  const exif = Buffer.concat([EXIF_HEADER, jsonBuf]);
  exif.writeUIntLE(jsonBuf.length, 14, 4);
  return exif;
}

// The extended (VP8X) header's feature flags, and its alpha bit.
const VP8X = 'VP8X';
const VP8X_FLAGS_OFFSET = 20;
const ALPHA_FLAG = 0x10;

function alphaFlag(webp: Buffer): number {
  // A simple webp has no VP8X header: its byte 20 is image data, not flags.
  if (webp.toString('ascii', 12, 16) !== VP8X) return 0;
  return webp[VP8X_FLAGS_OFFSET] & ALPHA_FLAG;
}

export default async function injectStickerExif(
  webpBuffer: Buffer,
  pack: string,
  author: string,
): Promise<Buffer> {
  const img = new WebPImage();
  await img.load(webpBuffer);
  img.exif = buildExifPayload(pack, author);
  const webp = await img.save(null);
  // node-webpmux rewrites the header without the alpha bit for lossy frames carrying an
  // ALPH chunk, and decoders then paint a transparent pad opaque black: keep the input's.
  webp[VP8X_FLAGS_OFFSET] |= alphaFlag(webpBuffer);
  return webp;
}
