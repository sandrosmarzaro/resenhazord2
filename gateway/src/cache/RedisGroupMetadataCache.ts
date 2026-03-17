import type { GroupMetadata } from '@whiskeysockets/baileys';
import type { Redis } from '@upstash/redis';
import type { CachePort } from './CachePort.js';

const TTL = 3600;

export default class RedisGroupMetadataCache implements CachePort<GroupMetadata> {
  constructor(private readonly redis: Redis) {}

  async get(key: string): Promise<GroupMetadata | undefined> {
    return (await this.redis.get<GroupMetadata>(key)) ?? undefined;
  }

  async set(key: string, value: GroupMetadata): Promise<void> {
    await this.redis.set(key, value, { ex: TTL });
  }
}
