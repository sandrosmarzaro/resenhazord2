import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { Boom } from '@hapi/boom';
import { DisconnectReason } from '@whiskeysockets/baileys';
import type { MongoDBAuthResult } from '../../../src/auth/MongoDBAuthState.js';
import ConnectionUpdateEvent from '../../../src/events/ConnectionUpdateEvent.js';
import ConnectionWatchdog from '../../../src/infra/ConnectionWatchdog.js';
import ConnectionState from '../../../src/infra/ConnectionState.js';
import Resenhazord2 from '../../../src/models/Resenhazord2.js';
import { Sentry } from '../../../src/infra/Sentry.js';
import logger from '../../../src/infra/Logger.js';

// Baileys builds a far larger AuthenticationState at runtime; these fixtures carry only
// the two fields that decide whether a pairing still exists.
function authStateWith(creds: { registered: boolean; me?: { id: string } }): MongoDBAuthResult {
  return { state: { creds }, saveCreds: vi.fn() } as unknown as MongoDBAuthResult;
}

const pairedAuthState = () =>
  authStateWith({ registered: true, me: { id: '5511999999999:1@s.whatsapp.net' } });

const unpairedAuthState = () => authStateWith({ registered: false });

describe('ConnectionUpdateEvent watchdog wiring', () => {
  beforeEach(() => {
    ConnectionUpdateEvent.reset();
    Resenhazord2.auth_state = pairedAuthState();
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
      'WhatsApp session unpaired; re-pair required before the bot can receive messages',
      'fatal',
    );
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

  it('reconnects when the close carries no status code', async () => {
    vi.spyOn(ConnectionWatchdog, 'arm').mockImplementation(() => {});
    const scheduleReconnect = vi
      .spyOn(ConnectionUpdateEvent, 'scheduleReconnect')
      .mockResolvedValue();

    await ConnectionUpdateEvent.run({
      connection: 'close',
      lastDisconnect: { error: new Error('socket hang up'), date: new Date() },
    });

    expect(scheduleReconnect).toHaveBeenCalledOnce();
  });
});

// Baileys defaults to 500 for every websocket or stream error it cannot classify
// (`getCodeFromWSError`, `getErrorCodeFromStreamError`), so the status code alone never
// proves the pairing died. Prod sat mute for 26h on 2026-07-24 because of that.
describe('ConnectionUpdateEvent unclassified 500 close', () => {
  beforeEach(() => {
    ConnectionUpdateEvent.reset();
    vi.spyOn(ConnectionState, 'markClosed').mockResolvedValue();
    vi.spyOn(ConnectionWatchdog, 'arm').mockImplementation(() => {});
    vi.spyOn(Sentry, 'captureMessage').mockReturnValue('');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const transportError = () =>
    new Boom(
      "WebSocket Error (WebSocket connection to 'wss://web.whatsapp.com/ws/chat' failed: Expected 101 status code)",
      { statusCode: DisconnectReason.badSession },
    );

  it('reconnects while the stored credentials are still paired', async () => {
    Resenhazord2.auth_state = pairedAuthState();
    const disable = vi.spyOn(ConnectionWatchdog, 'disable').mockImplementation(() => {});
    const scheduleReconnect = vi
      .spyOn(ConnectionUpdateEvent, 'scheduleReconnect')
      .mockResolvedValue();

    await ConnectionUpdateEvent.run({
      connection: 'close',
      lastDisconnect: { error: transportError(), date: new Date() },
    });

    expect(scheduleReconnect).toHaveBeenCalledOnce();
    expect(disable).not.toHaveBeenCalled();
  });

  it('gives up once the stored credentials confirm the pairing is gone', async () => {
    Resenhazord2.auth_state = unpairedAuthState();
    const disable = vi.spyOn(ConnectionWatchdog, 'disable').mockImplementation(() => {});
    const scheduleReconnect = vi
      .spyOn(ConnectionUpdateEvent, 'scheduleReconnect')
      .mockResolvedValue();

    await ConnectionUpdateEvent.run({
      connection: 'close',
      lastDisconnect: { error: transportError(), date: new Date() },
    });

    expect(disable).toHaveBeenCalledOnce();
    expect(scheduleReconnect).not.toHaveBeenCalled();
  });
});

// WhatsApp closes the stream naming the stanza it never got acked; Baileys keeps that
// node only in the Boom's `data`, and its own logger is silent.
describe('ConnectionUpdateEvent stream error detail', () => {
  const ackNode = { tag: 'ack', attrs: { class: 'message', type: 'text', id: '3EB0ABC' } };

  beforeEach(() => {
    ConnectionUpdateEvent.reset();
    Resenhazord2.auth_state = pairedAuthState();
    vi.spyOn(ConnectionState, 'markClosed').mockResolvedValue();
    vi.spyOn(ConnectionWatchdog, 'arm').mockImplementation(() => {});
    vi.spyOn(ConnectionUpdateEvent, 'scheduleReconnect').mockResolvedValue();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('records the stanza WhatsApp named when it closed the stream', async () => {
    const warn = vi.spyOn(logger, 'warn');
    const breadcrumb = vi.spyOn(Sentry, 'addBreadcrumb');
    const error = new Boom('Stream Errored (ack)', {
      statusCode: DisconnectReason.badSession,
      data: ackNode,
    });

    await ConnectionUpdateEvent.run({
      connection: 'close',
      lastDisconnect: { error, date: new Date() },
    });

    expect(warn).toHaveBeenCalledWith(
      expect.objectContaining({ event: 'connection_closed', errorData: ackNode }),
    );
    expect(breadcrumb).toHaveBeenCalledWith(
      expect.objectContaining({ data: expect.objectContaining({ errorData: ackNode }) }),
    );
  });
});
