import { describe, it, expect } from 'vitest';
import type { WAMessage } from '@whiskeysockets/baileys';

import InFlightCommands from '../../../src/bridge/InFlightCommands.js';

const original = { key: { id: 'ORIG', remoteJid: 'g@g.us' } } as WAMessage;

describe('InFlightCommands', () => {
  it('resolves a tracked id to its jid and original message', () => {
    const inFlight = new InFlightCommands();

    inFlight.track('corr-1', 'g@g.us', original);

    expect(inFlight.resolve('corr-1')).toEqual({ jid: 'g@g.us', quoted: original });
  });

  it('resolves a tracked id only once', () => {
    const inFlight = new InFlightCommands();
    inFlight.track('corr-1', 'g@g.us', original);

    inFlight.resolve('corr-1');

    expect(inFlight.resolve('corr-1')).toBeUndefined();
  });

  it('forgets the oldest command once more than its capacity go unanswered', () => {
    const inFlight = new InFlightCommands(2);
    inFlight.track('corr-1', 'g@g.us', original);
    inFlight.track('corr-2', 'g@g.us', original);

    inFlight.track('corr-3', 'g@g.us', original);

    expect(inFlight.resolve('corr-1')).toBeUndefined();
    expect(inFlight.resolve('corr-3')).toEqual({ jid: 'g@g.us', quoted: original });
  });

  it('resolves an unknown id to undefined', () => {
    const inFlight = new InFlightCommands();

    expect(inFlight.resolve('nope')).toBeUndefined();
  });
});
