import { Redis } from '@upstash/redis';
import type { GroupMetadata } from '@whiskeysockets/baileys';
import type { CachePort } from './CachePort.js';
import MemoryGroupMetadataCache from './MemoryGroupMetadataCache.js';
import RedisGroupMetadataCache from './RedisGroupMetadataCache.js';
import FallbackGroupMetadataCache from './FallbackGroupMetadataCache.js';
import StickerAudioStore from './StickerAudioStore.js';

function createRedis(): Redis | null {
  const url = process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN;
  return url && token ? new Redis({ url, token }) : null;
}

function createGroupMetadataCache(): CachePort<GroupMetadata> {
  const redis = createRedis();
  if (redis) {
    return new FallbackGroupMetadataCache(
      new RedisGroupMetadataCache(redis),
      new MemoryGroupMetadataCache(),
    );
  }
  return new MemoryGroupMetadataCache();
}

export const stickerAudioStore = new StickerAudioStore(createRedis());

export default createGroupMetadataCache();
