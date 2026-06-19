import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { Boom } from '@hapi/boom';
import { DisconnectReason } from '@whiskeysockets/baileys';
import ConnectionUpdateEvent from '../../../src/events/ConnectionUpdateEvent.js';
import ConnectionWatchdog from '../../../src/infra/ConnectionWatchdog.js';

describe('ConnectionUpdateEvent watchdog wiring', () => {
  beforeEach(() => {
    ConnectionUpdateEvent.reset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('disarms the watchdog once the connection opens', async () => {
    const disarm = vi.spyOn(ConnectionWatchdog, 'disarm').mockImplementation(() => {});

    await ConnectionUpdateEvent.run({ connection: 'open' });

    expect(disarm).toHaveBeenCalledOnce();
  });

  it('disables the watchdog when the session is logged out', async () => {
    const disable = vi.spyOn(ConnectionWatchdog, 'disable').mockImplementation(() => {});
    const error = new Boom('logged out', { statusCode: DisconnectReason.loggedOut });

    await ConnectionUpdateEvent.run({
      connection: 'close',
      lastDisconnect: { error, date: new Date() },
    });

    expect(disable).toHaveBeenCalledOnce();
  });

  it('arms the watchdog on a reconnectable close so a stalled reconnect still restarts', async () => {
    const arm = vi.spyOn(ConnectionWatchdog, 'arm').mockImplementation(() => {});
    vi.spyOn(ConnectionUpdateEvent, 'scheduleReconnect').mockResolvedValue();
    const error = new Boom('connection lost', { statusCode: DisconnectReason.connectionLost });

    await ConnectionUpdateEvent.run({
      connection: 'close',
      lastDisconnect: { error, date: new Date() },
    });

    expect(arm).toHaveBeenCalledOnce();
  });
});
