import { describe, it, expect } from 'vitest';

import InFlightCommands from '../../../src/bridge/InFlightCommands.js';

describe('InFlightCommands', () => {
  it('resolves a tracked id to its jid', () => {
    const inFlight = new InFlightCommands();

    inFlight.track('corr-1', 'g@g.us');

    expect(inFlight.resolve('corr-1')).toBe('g@g.us');
  });

  it('resolves a tracked id only once', () => {
    const inFlight = new InFlightCommands();
    inFlight.track('corr-1', 'g@g.us');

    inFlight.resolve('corr-1');

    expect(inFlight.resolve('corr-1')).toBeUndefined();
  });

  it('resolves an unknown id to undefined', () => {
    const inFlight = new InFlightCommands();

    expect(inFlight.resolve('nope')).toBeUndefined();
  });
});
