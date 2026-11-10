import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';

// Guards the bun patch that routes <status> stanzas through handleMessage. WhatsApp
// delivers a group status as <status from="<group>@g.us"> instead of <message>, and
// Baileys registers no handler for that tag: the stanza is dropped, never acked, and
// redelivered from the offline queue on every reconnect. Re-verify when bumping Baileys.
describe('Baileys status stanza patch', () => {
  it('routes the status tag through the message handler', () => {
    const require = createRequire(import.meta.url);
    const source = readFileSync(
      require.resolve('@whiskeysockets/baileys/lib/Socket/messages-recv.js'),
      'utf8',
    );

    expect(source).toMatch(
      /ws\.on\('CB:status', async \(node\) => \{\s*await processNode\('message', node, '[^']+', handleMessage\);/,
    );
  });
});
