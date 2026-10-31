import { MongoDBContainer, type StartedMongoDBContainer } from '@testcontainers/mongodb';
import type { Collection, MongoClient as MongoClientType } from 'mongodb';
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

import { useMongoDBAuthState } from '../../src/auth/MongoDBAuthState.js';

// tests/setup.ts mocks the driver for every other test.
const { MongoClient } = await vi.importActual<typeof import('mongodb')>('mongodb');

describe('useMongoDBAuthState', () => {
  // One round can pass by luck of scheduling; twenty can't.
  const ROUNDS = 20;
  const BURST = 5;
  const LAST_SAVED = BURST - 1;

  let container: StartedMongoDBContainer;
  let client: MongoClientType;
  let collection: Collection;

  beforeAll(async () => {
    container = await new MongoDBContainer('mongo:7').start();
    client = new MongoClient(container.getConnectionString(), { directConnection: true });
    collection = client.db('auth_state_test').collection('auth_state');
  }, 120_000);

  afterAll(async () => {
    await client.close();
    await container.stop();
  });

  beforeEach(async () => {
    await collection.deleteMany({});
  });

  async function saveBurst(): Promise<void> {
    const { state, saveCreds } = await useMongoDBAuthState(collection);
    const saves: Promise<void>[] = [];
    for (let saved = 0; saved < BURST; saved++) {
      state.creds.accountSyncCounter = saved;
      saves.push(saveCreds());
    }
    await Promise.all(saves);
  }

  async function storedCounter(): Promise<number> {
    const { state } = await useMongoDBAuthState(collection);
    return state.creds.accountSyncCounter;
  }

  it('keeps the last of simultaneous saves over existing creds', async () => {
    const { saveCreds } = await useMongoDBAuthState(collection);
    await saveCreds();

    for (let round = 0; round < ROUNDS; round++) {
      await saveBurst();

      expect(await storedCounter()).toBe(LAST_SAVED);
    }
  });

  it('keeps the last of simultaneous saves when no creds exist yet', async () => {
    for (let round = 0; round < ROUNDS; round++) {
      await collection.deleteMany({});

      await saveBurst();

      expect(await storedCounter()).toBe(LAST_SAVED);
    }
  });

  it('keeps saving after a restart reloads the stored creds', async () => {
    await saveBurst();
    const restarted = await useMongoDBAuthState(collection);
    restarted.state.creds.accountSyncCounter = BURST;

    await restarted.saveCreds();

    expect(await storedCounter()).toBe(BURST);
  });

  it('propagates a failed save', async () => {
    const failure = new Error('connection lost');
    const failing = {
      findOne: vi.fn().mockResolvedValue(null),
      updateOne: vi.fn().mockRejectedValue(failure),
    } as unknown as Collection; // Only the two calls saveCreds makes.
    const { saveCreds } = await useMongoDBAuthState(failing);

    await expect(saveCreds()).rejects.toBe(failure);
  });
});
