import { Image as WebPImage } from 'node-webpmux';

const EXIF_TAG_PACK = 0x4501;
const EXIF_TAG_AUTHOR = 0x4502;
const TIFF_TYPE_ASCII = 2;

function buildExifPayload(pack: string, author: string): Buffer {
  const packBuf = Buffer.from(pack, 'utf-8');
  const authorBuf = Buffer.from(author, 'utf-8');
  const packLen = packBuf.length + 1; // include null terminator
  const authorLen = authorBuf.length + 1;
  const packPadded = packLen + (packLen % 2); // pad to even for TIFF alignment

  const ifdSize = 2 + 2 * 12 + 4; // count + 2 entries + next IFD offset
  const dataStart = 8 + ifdSize; // after TIFF header + IFD

  // TIFF header (little-endian)
  const header = Buffer.from([0x49, 0x49, 0x2a, 0x00, 0x08, 0x00, 0x00, 0x00]);

  const ifd = Buffer.alloc(ifdSize);
  ifd.writeUInt16LE(2, 0); // 2 entries

  // Entry 1: pack name
  ifd.writeUInt16LE(EXIF_TAG_PACK, 2);
  ifd.writeUInt16LE(TIFF_TYPE_ASCII, 4);
  ifd.writeUInt32LE(packLen, 6);
  ifd.writeUInt32LE(dataStart, 10);

  // Entry 2: author
  ifd.writeUInt16LE(EXIF_TAG_AUTHOR, 14);
  ifd.writeUInt16LE(TIFF_TYPE_ASCII, 16);
  ifd.writeUInt32LE(authorLen, 18);
  ifd.writeUInt32LE(dataStart + packPadded, 22);

  // Next IFD offset = 0 (none)
  ifd.writeUInt32LE(0, 26);

  const packData = Buffer.concat([packBuf, Buffer.alloc(packPadded - packBuf.length)]);
  const authorData = Buffer.concat([authorBuf, Buffer.alloc(1)]); // null terminator

  return Buffer.concat([header, ifd, packData, authorData]);
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
