import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { access, unlink } from 'node:fs/promises';
import ConnectionState from '../../../src/infra/ConnectionState.js';

const exists = async (): Promise<boolean> =>
  access(ConnectionState.MARKER_PATH)
    .then(() => true)
    .catch(() => false);

describe('ConnectionState', () => {
  beforeEach(async () => {
    await unlink(ConnectionState.MARKER_PATH).catch(() => {});
  });

  afterEach(async () => {
    await unlink(ConnectionState.MARKER_PATH).catch(() => {});
  });

  it('writes the marker when the connection opens', async () => {
    await ConnectionState.markOpen();

    expect(await exists()).toBe(true);
  });

  it('removes the marker when the connection closes', async () => {
    await ConnectionState.markOpen();

    await ConnectionState.markClosed();

    expect(await exists()).toBe(false);
  });

  it('stays absent when closing an already closed connection', async () => {
    await ConnectionState.markClosed();

    expect(await exists()).toBe(false);
  });
});
