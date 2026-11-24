import { describe, it, expect, vi, afterEach } from 'vitest';

describe('cache wiring', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  async function loadWith(url: string, token: string) {
    vi.stubEnv('UPSTASH_REDIS_REST_URL', url);
    vi.stubEnv('UPSTASH_REDIS_REST_TOKEN', token);
    vi.resetModules();
    return import('../../../src/cache/index.js');
  }

  it('backs the group metadata cache with Upstash when configured', async () => {
    const { default: cache } = await loadWith('https://example.upstash.io', 'token');
    const { default: FallbackGroupMetadataCache } =
      await import('../../../src/cache/FallbackGroupMetadataCache.js');

    expect(cache).toBeInstanceOf(FallbackGroupMetadataCache);
  });

  it('keeps the group metadata in memory without Upstash', async () => {
    const { default: cache } = await loadWith('', '');
    const { default: MemoryGroupMetadataCache } =
      await import('../../../src/cache/MemoryGroupMetadataCache.js');

    expect(cache).toBeInstanceOf(MemoryGroupMetadataCache);
  });
});
