import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import injectStickerExif from '../../../src/utils/StickerExif.js';

describe('injectStickerExif', () => {
  const VP8X_FLAGS_OFFSET = 20;
  const ALPHA_FLAG = 0x10;
  const media = (name: string) =>
    readFileSync(new URL(`../../fixtures/media/${name}`, import.meta.url));
  const flags = (webp: Buffer) => webp[VP8X_FLAGS_OFFSET];

  it('writes the pack and the author', async () => {
    const webp = await injectStickerExif(media('transparent.webp'), 'Pack', 'Autor');

    expect(webp.toString('latin1')).toContain(
      '{"sticker-pack-name":"Pack","sticker-pack-publisher":"Autor"}',
    );
  });

  // node-webpmux rewrites the VP8X header without the alpha bit when every frame keeps
  // its ALPH chunk, so decoders paint a transparent pad opaque black.
  it('keeps a transparent sticker transparent', async () => {
    const webp = await injectStickerExif(media('transparent.webp'), 'Pack', 'Autor');

    expect(flags(webp) & ALPHA_FLAG).toBe(ALPHA_FLAG);
  });

  // A simple webp has no VP8X header: its byte 20 is image data, not flags.
  it('gives a simple webp no alpha it never had', async () => {
    const webp = await injectStickerExif(media('still.webp'), 'Pack', 'Autor');

    expect(flags(webp) & ALPHA_FLAG).toBe(0);
  });

  it('leaves an opaque sticker opaque', async () => {
    const webp = await injectStickerExif(media('animated.webp'), 'Pack', 'Autor');

    expect(flags(webp) & ALPHA_FLAG).toBe(0);
  });
});
