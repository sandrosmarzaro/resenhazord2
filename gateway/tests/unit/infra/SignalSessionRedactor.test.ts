import { describe, it, expect, vi } from 'vitest';
import { createRequire } from 'node:module';
import SignalSessionRedactor from '../../../src/infra/SignalSessionRedactor.js';

const require = createRequire(import.meta.url);
const { SessionRecord } = require('libsignal') as { SessionRecord: { createEntry(): object } };

function fakeConsole(): Console {
  return {
    log: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  } as unknown as Console;
}

describe('SignalSessionRedactor', () => {
  it('replaces a libsignal session entry with a placeholder, keeping the message', () => {
    const target = fakeConsole();
    const print = target.info;
    SignalSessionRedactor.install(target);

    target.info('Closing session:', SessionRecord.createEntry());

    expect(print).toHaveBeenCalledWith('Closing session:', '[SessionEntry redacted]');
  });

  it('passes ordinary arguments through untouched', () => {
    const target = fakeConsole();
    const print = target.warn;
    SignalSessionRedactor.install(target);

    target.warn('Closing open session in favor of incoming prekey bundle', { id: 1 });

    expect(print).toHaveBeenCalledWith('Closing open session in favor of incoming prekey bundle', {
      id: 1,
    });
  });
});
