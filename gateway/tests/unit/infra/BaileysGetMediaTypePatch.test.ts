import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';

// Guards the bun patch on Baileys' internal getMediaType. It checks message.imageMessage
// directly, so a wrapped message (view-once, WhiskeySockets/Baileys#2435; group status)
// returns '' and the enc node ships type="media" with no mediatype, which WhatsApp drops.
// getMediaType is not exported, so we assert the patch is present in the installed
// source. Re-verify this when bumping @whiskeysockets/baileys.
describe('Baileys getMediaType patch', () => {
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

  it('unwraps the viewOnceMessage wrapper', () => {
    const region = patchedGetMediaTypeSource();

    expect(region).toContain('viewOnceMessage?.message');
    expect(region).toContain('viewOnceMessageV2?.message');
  });

  it('unwraps the groupStatusMessage wrapper', () => {
    const region = patchedGetMediaTypeSource();

    expect(region).toContain('groupStatusMessage?.message');
    expect(region).toContain('groupStatusMessageV2?.message');
  });

  it('unwraps before the plain imageMessage lookup, so it takes effect', () => {
    const region = patchedGetMediaTypeSource();

    expect(region.indexOf('viewOnceMessage?.message')).toBeLessThan(
      region.indexOf('message.imageMessage'),
    );
  });
});
