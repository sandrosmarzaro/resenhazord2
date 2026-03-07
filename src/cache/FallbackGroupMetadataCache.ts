import type { GroupMetadata } from '@whiskeysockets/baileys';
import type { CachePort } from './CachePort.js';

export default class FallbackGroupMetadataCache implements CachePort<GroupMetadata> {
  constructor(
    private readonly primary: CachePort<GroupMetadata>,
    private readonly fallback: CachePort<GroupMetadata>,
  ) {}

  async get(key: string): Promise<GroupMetadata | undefined> {
    try {
      const value = await this.primary.get(key);
      if (value !== undefined) return value;
    } catch {
      // ignore
    }
    return this.fallback.get(key);
  }

  async set(key: string, value: GroupMetadata): Promise<void> {
    await this.fallback.set(key, value);
    try {
      await this.primary.set(key, value);
    } catch {
      // ignore
    }
  }
}
