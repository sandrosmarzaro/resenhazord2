import { Image as WebPImage } from 'node-webpmux';

const EXIF_HEADER = Buffer.from([
  0x49, 0x49, 0x2a, 0x00, 0x08, 0x00, 0x00, 0x00, 0x01, 0x00, 0x41, 0x57, 0x07, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x16, 0x00, 0x00, 0x00,
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

export default async function injectStickerExif(
  webpBuffer: Buffer,
  pack: string,
  author: string,
): Promise<Buffer> {
  const img = new WebPImage();
  await img.load(webpBuffer);
  img.exif = buildExifPayload(pack, author);
  return (await img.save(null)) as Buffer;
}
