import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { Boom } from '@hapi/boom';
import { DisconnectReason } from '@whiskeysockets/baileys';
import ConnectionUpdateEvent from '../../../src/events/ConnectionUpdateEvent.js';
import ConnectionWatchdog from '../../../src/infra/ConnectionWatchdog.js';
import ConnectionState from '../../../src/infra/ConnectionState.js';
import { Sentry } from '../../../src/infra/Sentry.js';

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

  it('marks the connection state open so the healthcheck sees a live session', async () => {
    vi.spyOn(ConnectionWatchdog, 'disarm').mockImplementation(() => {});
    const markOpen = vi.spyOn(ConnectionState, 'markOpen').mockResolvedValue();

    await ConnectionUpdateEvent.run({ connection: 'open' });

    expect(markOpen).toHaveBeenCalledOnce();
  });

  it('clears the connection state on close so the healthcheck turns unhealthy', async () => {
    vi.spyOn(ConnectionWatchdog, 'disable').mockImplementation(() => {});
    const markClosed = vi.spyOn(ConnectionState, 'markClosed').mockResolvedValue();
    const error = new Boom('logged out', { statusCode: DisconnectReason.loggedOut });

    await ConnectionUpdateEvent.run({
      connection: 'close',
      lastDisconnect: { error, date: new Date() },
    });

    expect(markClosed).toHaveBeenCalledOnce();
  });

  it('reports a logged out session as fatal', async () => {
    vi.spyOn(ConnectionWatchdog, 'disable').mockImplementation(() => {});
    vi.spyOn(ConnectionState, 'markClosed').mockResolvedValue();
    const capture = vi.spyOn(Sentry, 'captureMessage').mockReturnValue('');
    const error = new Boom('logged out', { statusCode: DisconnectReason.loggedOut });

    await ConnectionUpdateEvent.run({
      connection: 'close',
      lastDisconnect: { error, date: new Date() },
    });

    expect(capture).toHaveBeenCalledWith(
      'Bot logged out; re-pair required before it can receive messages',
      'fatal',
    );
  });

  it('disables the watchdog when the session is bad', async () => {
    const disable = vi.spyOn(ConnectionWatchdog, 'disable').mockImplementation(() => {});
    const error = new Boom('bad session', { statusCode: DisconnectReason.badSession });

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
