import { Redis } from '@upstash/redis';
import type { GroupMetadata } from '@whiskeysockets/baileys';
import type { CachePort } from './CachePort.js';
import MemoryGroupMetadataCache from './MemoryGroupMetadataCache.js';
import RedisGroupMetadataCache from './RedisGroupMetadataCache.js';
import FallbackGroupMetadataCache from './FallbackGroupMetadataCache.js';

function createGroupMetadataCache(): CachePort<GroupMetadata> {
  const url = process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN;
  if (url && token) {
    const redis = new Redis({ url, token });
    return new FallbackGroupMetadataCache(
      new RedisGroupMetadataCache(redis),
      new MemoryGroupMetadataCache(),
    );
  }
  return new MemoryGroupMetadataCache();
}

export default createGroupMetadataCache();
