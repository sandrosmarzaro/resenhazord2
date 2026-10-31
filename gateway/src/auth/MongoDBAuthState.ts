import type { Collection } from 'mongodb';
import type { AuthenticationState } from '@whiskeysockets/baileys';
import { proto, initAuthCreds, BufferJSON } from '@whiskeysockets/baileys';

export interface MongoDBAuthResult {
  state: AuthenticationState;
  saveCreds: () => Promise<void>;
}

function safeId(id: string): string {
  if (typeof id !== 'string') throw new TypeError('id must be a string');
  return id;
}

function isDuplicateKey(error: unknown): boolean {
  const duplicateKeyCode = 11000;
  return (
    typeof error === 'object' &&
    error !== null &&
    'code' in error &&
    error.code === duplicateKeyCode
  );
}

export const useMongoDBAuthState = async (collection: Collection): Promise<MongoDBAuthResult> => {
  const col = collection as unknown as Collection<{ _id: string; data: string; version?: number }>;

  const writeData = async (data: unknown, id: string) => {
    await col.replaceOne(
      { _id: safeId(id) },
      { data: JSON.stringify(data, BufferJSON.replacer) } as { _id: string; data: string },
      { upsert: true },
    );
  };

  const readData = async (id: string) => {
    const doc = await col.findOne({ _id: safeId(id) });
    if (!doc) return null;
    return JSON.parse(doc.data, BufferJSON.reviver);
  };

  const removeData = async (id: string) => {
    await col.deleteOne({ _id: safeId(id) });
  };

  const storedCreds = await col.findOne({ _id: 'creds' });
  const creds = storedCreds ? JSON.parse(storedCreds.data, BufferJSON.reviver) : initAuthCreds();
  let credsVersion = storedCreds?.version ?? 0;

  const getKeys: AuthenticationState['keys']['get'] = async (type, ids) => {
    const data: Record<string, unknown> = {};
    await Promise.all(
      ids.map(async (id) => {
        let value = await readData(`${type}-${id}`);
        if (type === 'app-state-sync-key' && value) {
          value = proto.Message.AppStateSyncKeyData.fromObject(value);
        }
        data[id] = value;
      }),
    );
    return data as never;
  };

  const setKeys: AuthenticationState['keys']['set'] = async (data) => {
    const tasks: Promise<void>[] = [];
    for (const category in data) {
      for (const id in (data as Record<string, Record<string, unknown>>)[category]) {
        const value = (data as Record<string, Record<string, unknown>>)[category][id];
        tasks.push(value ? writeData(value, `${category}-${id}`) : removeData(`${category}-${id}`));
      }
    }
    await Promise.all(tasks);
  };

  // Pooled connections can land concurrent writes out of order, and unlike the keys, which
  // Baileys queues by type, nothing queues creds.update. The version makes a late older
  // snapshot miss the filter instead of overwriting a newer one.
  const saveCreds = async () => {
    credsVersion += 1;
    const query = { _id: 'creds', version: { $not: { $gte: credsVersion } } };
    const update = {
      $set: { data: JSON.stringify(creds, BufferJSON.replacer), version: credsVersion },
    };
    try {
      await col.updateOne(query, update, { upsert: true });
    } catch (error) {
      if (!isDuplicateKey(error)) throw error;
      // The filter missed: a newer write landed, or another save just created the document.
      await col.updateOne(query, update);
    }
  };

  return {
    state: {
      creds,
      keys: { get: getKeys, set: setKeys },
    },
    saveCreds,
  };
};
