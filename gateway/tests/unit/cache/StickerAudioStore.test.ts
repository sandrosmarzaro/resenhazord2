import { describe, it, expect, vi } from 'vitest';
import type { Redis } from '@upstash/redis';
import StickerAudioStore from '../../../src/cache/StickerAudioStore.js';

function mapBackedRedis(): Redis {
  const entries = new Map<string, unknown>();
  return {
    get: vi.fn(async (key: string) => entries.get(key) ?? null),
    set: vi.fn(async (key: string, value: unknown) => {
      entries.set(key, value);
      return 'OK';
    }),
  } as unknown as Redis;
}

describe('StickerAudioStore', () => {
  const key = { remoteJid: 'group@g.us', id: 'STICKER1' };
  const audio = {
    url: 'https://mmg.whatsapp.net/audio',
    mimetype: 'audio/ogg; codecs=opus',
    mediaKey: new Uint8Array([1, 2, 3]),
    seconds: 8,
  };

  it('keeps the audio for seven days under the chat and message id', async () => {
    const redis = mapBackedRedis();

    await new StickerAudioStore(redis).save(key, audio);

    expect(redis.set).toHaveBeenCalledWith(
      'sticker-audio:group@g.us:STICKER1',
      { audio: expect.any(String) },
      { ex: 604800 },
    );
  });

  it('finds the saved audio, media key bytes included', async () => {
    const store = new StickerAudioStore(mapBackedRedis());
    await store.save(key, audio);

    const found = await store.find('group@g.us', 'STICKER1');

    expect(found).toMatchObject({ ...audio, mediaKey: Buffer.from([1, 2, 3]) });
  });

  it('finds nothing for a sticker it never saw', async () => {
    const store = new StickerAudioStore(mapBackedRedis());

    expect(await store.find('group@g.us', 'OTHER')).toBeUndefined();
  });

  it('does nothing without redis', async () => {
    const store = new StickerAudioStore(null);
    await store.save(key, audio);

    expect(await store.find('group@g.us', 'STICKER1')).toBeUndefined();
  });
});
