import { describe, it, expect, beforeEach, vi } from 'vitest';
import type { Redis } from '@upstash/redis';
import RedisGroupMetadataCache from '../../../src/cache/RedisGroupMetadataCache.js';
import { GroupMetadataFactory } from '../../fixtures/index.js';

function mockRedis(overrides: Partial<Record<keyof Redis, unknown>> = {}): Redis {
  return {
    get: vi.fn(),
    set: vi.fn(),
    ...overrides,
  } as unknown as Redis;
}

describe('RedisGroupMetadataCache', () => {
  let redis: Redis;
  let cache: RedisGroupMetadataCache;

  beforeEach(() => {
    redis = mockRedis();
    cache = new RedisGroupMetadataCache(redis);
  });

  it('returns undefined when redis.get returns null', async () => {
    vi.mocked(redis.get).mockResolvedValue(null);
    expect(await cache.get('key')).toBeUndefined();
  });

  it('returns the value when redis.get returns data', async () => {
    const group = GroupMetadataFactory.build();
    vi.mocked(redis.get).mockResolvedValue(group);
    expect(await cache.get(group.id)).toEqual(group);
  });

  it('calls redis.set with TTL of 3600', async () => {
    vi.mocked(redis.set).mockResolvedValue('OK');
    const group = GroupMetadataFactory.build();
    await cache.set(group.id, group);
    expect(redis.set).toHaveBeenCalledWith(group.id, group, { ex: 3600 });
  });
});
