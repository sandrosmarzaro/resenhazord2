import { describe, it, expect, beforeEach } from 'vitest';
import MemoryGroupMetadataCache from '../../../src/cache/MemoryGroupMetadataCache.js';
import { GroupMetadataFactory } from '../../fixtures/index.js';

describe('MemoryGroupMetadataCache', () => {
  let cache: MemoryGroupMetadataCache;

  beforeEach(() => {
    cache = new MemoryGroupMetadataCache();
  });

  it('returns undefined for unknown keys', async () => {
    expect(await cache.get('unknown')).toBeUndefined();
  });

  it('stores and retrieves a value', async () => {
    const group = GroupMetadataFactory.build();
    await cache.set(group.id, group);
    expect(await cache.get(group.id)).toEqual(group);
  });

  it('overwrites an existing value', async () => {
    const group = GroupMetadataFactory.build();
    const updated = { ...group, subject: 'Updated' };
    await cache.set(group.id, group);
    await cache.set(group.id, updated);
    expect((await cache.get(group.id))?.subject).toBe('Updated');
  });
});
