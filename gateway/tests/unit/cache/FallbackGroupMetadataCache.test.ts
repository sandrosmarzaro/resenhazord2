import { describe, it, expect, beforeEach, vi } from 'vitest';
import type { CachePort } from '../../../src/cache/CachePort.js';
import type { GroupMetadata } from '@whiskeysockets/baileys';
import FallbackGroupMetadataCache from '../../../src/cache/FallbackGroupMetadataCache.js';
import { GroupMetadataFactory } from '../../fixtures/index.js';

function mockCache(): CachePort<GroupMetadata> {
  return {
    get: vi.fn(),
    set: vi.fn(),
  };
}

describe('FallbackGroupMetadataCache', () => {
  let primary: CachePort<GroupMetadata>;
  let fallback: CachePort<GroupMetadata>;
  let cache: FallbackGroupMetadataCache;

  beforeEach(() => {
    primary = mockCache();
    fallback = mockCache();
    cache = new FallbackGroupMetadataCache(primary, fallback);
  });

  describe('get', () => {
    it('returns primary value when found', async () => {
      const group = GroupMetadataFactory.build();
      vi.mocked(primary.get).mockResolvedValue(group);
      expect(await cache.get(group.id)).toEqual(group);
      expect(fallback.get).not.toHaveBeenCalled();
    });

    it('falls back to memory when primary returns undefined', async () => {
      const group = GroupMetadataFactory.build();
      vi.mocked(primary.get).mockResolvedValue(undefined);
      vi.mocked(fallback.get).mockResolvedValue(group);
      expect(await cache.get(group.id)).toEqual(group);
    });

    it('falls back to memory when primary throws', async () => {
      const group = GroupMetadataFactory.build();
      vi.mocked(primary.get).mockRejectedValue(new Error('Redis down'));
      vi.mocked(fallback.get).mockResolvedValue(group);
      expect(await cache.get(group.id)).toEqual(group);
    });
  });

  describe('set', () => {
    it('writes to fallback first, then primary', async () => {
      vi.mocked(fallback.set).mockResolvedValue(undefined);
      vi.mocked(primary.set).mockResolvedValue(undefined);
      const group = GroupMetadataFactory.build();
      await cache.set(group.id, group);
      expect(fallback.set).toHaveBeenCalledWith(group.id, group);
      expect(primary.set).toHaveBeenCalledWith(group.id, group);
    });

    it('does not throw when primary.set fails', async () => {
      vi.mocked(fallback.set).mockResolvedValue(undefined);
      vi.mocked(primary.set).mockRejectedValue(new Error('Redis down'));
      const group = GroupMetadataFactory.build();
      await expect(cache.set(group.id, group)).resolves.toBeUndefined();
    });
  });
});
