import type { Collection } from 'mongodb';
import type { AuthenticationState } from '@whiskeysockets/baileys';
import { proto, initAuthCreds, BufferJSON } from '@whiskeysockets/baileys';

export interface MongoDBAuthResult {
  state: AuthenticationState;
  saveCreds: () => Promise<void>;
}

export const useMongoDBAuthState = async (collection: Collection): Promise<MongoDBAuthResult> => {
  const col = collection as unknown as Collection<{ _id: string; data: string }>;

  const writeData = async (data: unknown, id: string) => {
    await col.replaceOne(
      { _id: id },
      { data: JSON.stringify(data, BufferJSON.replacer) } as { _id: string; data: string },
      { upsert: true },
    );
  };

  const readData = async (id: string) => {
    const doc = await col.findOne({ _id: id });
    if (!doc) return null;
    return JSON.parse(doc.data, BufferJSON.reviver);
  };

  const removeData = async (id: string) => {
    await col.deleteOne({ _id: id });
  };

  const creds = (await readData('creds')) || initAuthCreds();

  return {
    state: {
      creds,
      keys: {
        get: async (type, ids) => {
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
        },
        set: async (data) => {
          const tasks: Promise<void>[] = [];
          for (const category in data) {
            for (const id in (data as Record<string, Record<string, unknown>>)[category]) {
              const value = (data as Record<string, Record<string, unknown>>)[category][id];
              tasks.push(
                value ? writeData(value, `${category}-${id}`) : removeData(`${category}-${id}`),
              );
            }
          }
          await Promise.all(tasks);
        },
      },
    },
    saveCreds: async () => {
      await writeData(creds, 'creds');
    },
  };
};
