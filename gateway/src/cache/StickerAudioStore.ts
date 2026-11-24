import type { Redis } from '@upstash/redis';
import { proto, type WAMessageKey } from '@whiskeysockets/baileys';

interface StoredAudio {
  audio: string;
}

// A quoted audio sticker arrives stripped of its audio (Web and Android alike), so the
// audio of every audio sticker the bot sees is kept here, found again by the reply's
// stanzaId. Without Redis (local dev) a quoted sticker just comes out silent.
export default class StickerAudioStore {
  private static readonly TTL_SECONDS = 7 * 24 * 60 * 60;

  constructor(private readonly redis: Redis | null) {}

  async save(key: WAMessageKey, audio: proto.Message.IAudioMessage): Promise<void> {
    if (!this.redis) return;
    const encoded = proto.Message.AudioMessage.encode(audio).finish();
    const value: StoredAudio = { audio: Buffer.from(encoded).toString('base64') };
    await this.redis.set(StickerAudioStore.key(key.remoteJid!, key.id!), value, {
      ex: StickerAudioStore.TTL_SECONDS,
    });
  }

  async find(jid: string, messageId: string): Promise<proto.Message.IAudioMessage | undefined> {
    if (!this.redis) return undefined;
    const stored = await this.redis.get<StoredAudio>(StickerAudioStore.key(jid, messageId));
    if (!stored) return undefined;
    return proto.Message.AudioMessage.decode(Buffer.from(stored.audio, 'base64'));
  }

  private static key(jid: string, messageId: string): string {
    return `sticker-audio:${jid}:${messageId}`;
  }
}
