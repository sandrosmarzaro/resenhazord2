import type { GroupMetadata } from '@whiskeysockets/baileys';
import type { CachePort } from './CachePort.js';

export default class MemoryGroupMetadataCache implements CachePort<GroupMetadata> {
  private readonly store = new Map<string, GroupMetadata>();

  async get(key: string): Promise<GroupMetadata | undefined> {
    return this.store.get(key);
  }

  async set(key: string, value: GroupMetadata): Promise<void> {
    this.store.set(key, value);
  }
}
