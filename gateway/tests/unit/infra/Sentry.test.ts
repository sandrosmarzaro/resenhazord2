import { describe, it, expect, vi } from 'vitest';
import { init } from '@sentry/bun';

import '../../../src/infra/Sentry.js';

describe('Sentry', () => {
  it('leaves unhandled rejections to our handler so a 1006 sends no event', () => {
    const defaults = [{ name: 'OnUnhandledRejection' }, { name: 'Http' }];
    const { integrations } = vi.mocked(init).mock.calls[0][0] ?? {};

    const kept = typeof integrations === 'function' ? integrations(defaults) : integrations;

    expect(kept?.map((integration) => integration.name)).toEqual(['Http', 'ConsoleLogs']);
  });
});
