import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';

// Guards the bun patch for WhiskeySockets/Baileys#2435. Baileys' internal getMediaType
// checks message.imageMessage directly; a view-once message is wrapped in viewOnceMessage,
// so without the patch it returns '' — the enc node ships an empty mediatype and WhatsApp
// drops the media. getMediaType is not exported, so we assert the patch is present in the
// installed source. Re-verify this when bumping @whiskeysockets/baileys.
describe('Baileys view-once patch (getMediaType)', () => {
  function patchedGetMediaTypeSource(): string {
    const require = createRequire(import.meta.url);
    const source = readFileSync(
      require.resolve('@whiskeysockets/baileys/lib/Socket/messages-send.js'),
      'utf8',
    );
    const start = source.indexOf('const getMediaType = (message) => {');
    expect(start).toBeGreaterThan(-1);
    return source.slice(start, start + 600);
  }

  it('unwraps the viewOnceMessage wrapper inside getMediaType', () => {
    const region = patchedGetMediaTypeSource();

    expect(region).toContain('viewOnceMessage?.message');
    expect(region).toContain('viewOnceMessageV2?.message');
  });

  it('unwraps before the plain imageMessage lookup, so it takes effect', () => {
    const region = patchedGetMediaTypeSource();

    expect(region.indexOf('viewOnceMessage?.message')).toBeLessThan(
      region.indexOf('message.imageMessage'),
    );
  });
});
