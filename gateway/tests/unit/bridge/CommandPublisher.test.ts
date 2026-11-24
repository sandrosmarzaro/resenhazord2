import { describe, it, expect, vi } from 'vitest';

import CommandPublisher from '../../../src/bridge/CommandPublisher.js';
import type BrokerPort from '../../../src/ports/BrokerPort.js';
import type MediaHandler from '../../../src/bridge/MediaHandler.js';
import type StickerAudioStore from '../../../src/cache/StickerAudioStore.js';
import { injectPublishTrace } from '../../../src/infra/Otel.js';
import { createMockBrokerPort } from '../../fixtures/factories/MockBrokerPort.js';
import { GroupCommandData } from '../../fixtures/index.js';

vi.mock('../../../src/infra/Otel.js', () => ({ injectPublishTrace: vi.fn() }));

function makeBroker(): BrokerPort {
  return createMockBrokerPort();
}

function audioStore(audio?: object): StickerAudioStore {
  return { find: vi.fn().mockResolvedValue(audio) } as unknown as StickerAudioStore;
}

function publishedEnvelope(broker: BrokerPort): { id: string; data: Record<string, unknown> } {
  const body = (broker.publish as ReturnType<typeof vi.fn>).mock.calls[0][1] as Buffer;
  return JSON.parse(body.toString());
}

describe('CommandPublisher', () => {
  describe('without media', () => {
    it('publishes a command envelope to the commands queue', async () => {
      const broker = makeBroker();
      const mediaHandler = {
        detectMedia: vi.fn().mockReturnValue(null),
      } as unknown as MediaHandler;
      const data = GroupCommandData.build({ text: ',ping' });

      const id = await new CommandPublisher(broker, mediaHandler, audioStore()).publish(data);

      expect(broker.publish).toHaveBeenCalledOnce();
      const [queue] = (broker.publish as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(queue).toBe('commands');
      const envelope = publishedEnvelope(broker);
      expect(envelope.id).toBe(id);
      expect(envelope.data.text).toBe(',ping');
      expect(envelope.data.jid).toBe(data.key.remoteJid);
      expect(envelope.data.is_group).toBe(true);
      expect(envelope.data.media_buffer_b64).toBeUndefined();
    });

    it('opens a publish trace on the envelope for edge->core continuity', async () => {
      const broker = makeBroker();
      const mediaHandler = {
        detectMedia: vi.fn().mockReturnValue(null),
      } as unknown as MediaHandler;
      const data = GroupCommandData.build({ text: ',ping' });
      vi.mocked(injectPublishTrace).mockClear();

      await new CommandPublisher(broker, mediaHandler, audioStore()).publish(data);

      expect(injectPublishTrace).toHaveBeenCalledOnce();
      const carrier = (injectPublishTrace as ReturnType<typeof vi.fn>).mock.calls[0][0];
      expect(carrier).toHaveProperty('id');
      expect(carrier).toHaveProperty('data');
    });

    it('carries mentions and the quoted text', async () => {
      const broker = makeBroker();
      const mediaHandler = {
        detectMedia: vi.fn().mockReturnValue(null),
      } as unknown as MediaHandler;
      const data = GroupCommandData.build(
        { text: ',ban' },
        { transient: { isGroup: true, mentionedJids: ['victim@s'], hasQuotedMessage: true } },
      );

      await new CommandPublisher(broker, mediaHandler, audioStore()).publish(data);

      const envelope = publishedEnvelope(broker);
      expect(envelope.data.mentioned_jids).toEqual(['victim@s']);
      expect(envelope.data.quoted_text).toBe('quoted message');
    });
  });

  describe('sender_jid addressing', () => {
    it('uses the phone-number JID (participantAlt) in lid-addressed groups', async () => {
      const broker = makeBroker();
      const mediaHandler = {
        detectMedia: vi.fn().mockReturnValue(null),
      } as unknown as MediaHandler;
      const data = GroupCommandData.build({ text: ',grupo exit test' });
      data.key.participant = '253278650671105@lid';
      data.key.participantAlt = '5528999223882@s.whatsapp.net';
      data.key.addressingMode = 'lid';

      await new CommandPublisher(broker, mediaHandler, audioStore()).publish(data);

      const envelope = publishedEnvelope(broker);
      expect(envelope.data.sender_jid).toBe('5528999223882@s.whatsapp.net');
    });

    it('keeps participant as sender_jid when not lid-addressed', async () => {
      const broker = makeBroker();
      const mediaHandler = {
        detectMedia: vi.fn().mockReturnValue(null),
      } as unknown as MediaHandler;
      const data = GroupCommandData.build({ text: ',grupo exit test' });
      data.key.participant = '5528999223882@s.whatsapp.net';

      await new CommandPublisher(broker, mediaHandler, audioStore()).publish(data);

      const envelope = publishedEnvelope(broker);
      expect(envelope.data.sender_jid).toBe('5528999223882@s.whatsapp.net');
    });

    it('falls back to participant when lid-addressed without participantAlt', async () => {
      const broker = makeBroker();
      const mediaHandler = {
        detectMedia: vi.fn().mockReturnValue(null),
      } as unknown as MediaHandler;
      const data = GroupCommandData.build({ text: ',grupo exit test' });
      data.key.participant = '253278650671105@lid';
      data.key.addressingMode = 'lid';

      await new CommandPublisher(broker, mediaHandler, audioStore()).publish(data);

      const envelope = publishedEnvelope(broker);
      expect(envelope.data.sender_jid).toBe('253278650671105@lid');
    });

    it('falls back to remoteJid when there is no participant', async () => {
      const broker = makeBroker();
      const mediaHandler = {
        detectMedia: vi.fn().mockReturnValue(null),
      } as unknown as MediaHandler;
      const data = GroupCommandData.build({ text: ',grupo exit test' });
      data.key.participant = undefined;

      await new CommandPublisher(broker, mediaHandler, audioStore()).publish(data);

      const envelope = publishedEnvelope(broker);
      expect(envelope.data.sender_jid).toBe(data.key.remoteJid);
    });

    it('falls back to remoteJid when the participant is an empty string', async () => {
      const broker = makeBroker();
      const mediaHandler = {
        detectMedia: vi.fn().mockReturnValue(null),
      } as unknown as MediaHandler;
      const data = GroupCommandData.build({ text: ',dl https://x.com/a' });
      data.key.participant = '';

      await new CommandPublisher(broker, mediaHandler, audioStore()).publish(data);

      const envelope = publishedEnvelope(broker);
      expect(envelope.data.sender_jid).toBe(data.key.remoteJid);
    });
  });

  describe('with media', () => {
    it('downloads the media and inlines it as base64', async () => {
      const broker = makeBroker();
      const buffer = Buffer.from([1, 2, 3]);
      const mediaHandler = {
        detectMedia: vi.fn().mockReturnValue({ type: 'sticker', source: 'quoted' }),
        downloadMedia: vi.fn().mockResolvedValue(buffer),
      } as unknown as MediaHandler;
      const data = GroupCommandData.build({ text: ',sticker' });

      await new CommandPublisher(broker, mediaHandler, audioStore()).publish(data);

      const envelope = publishedEnvelope(broker);
      expect(envelope.data.media_type).toBe('sticker');
      expect(envelope.data.media_buffer_b64).toBe(buffer.toString('base64'));
    });

    it('publishes without the buffer when the download fails', async () => {
      const broker = makeBroker();
      const mediaHandler = {
        detectMedia: vi.fn().mockReturnValue({ type: 'image', source: 'direct' }),
        downloadMedia: vi.fn().mockRejectedValue(new Error('boom')),
      } as unknown as MediaHandler;
      const data = GroupCommandData.build({ text: ',extract' });

      await new CommandPublisher(broker, mediaHandler, audioStore()).publish(data);

      const envelope = publishedEnvelope(broker);
      expect(envelope.data.media_type).toBe('image');
      expect(envelope.data.media_buffer_b64).toBeUndefined();
    });
  });

  describe('quoted audio sticker', () => {
    const audio = { url: 'https://mmg.whatsapp.net/audio', mimetype: 'audio/ogg; codecs=opus' };
    const sticker = Buffer.from([1, 2, 3]);
    const sound = Buffer.from([4, 5, 6]);

    function quotingSticker() {
      const data = GroupCommandData.build(
        { text: ',extrair' },
        { transient: { hasQuotedStickerMessage: true } },
      );
      const contextInfo = data.message!.extendedTextMessage!.contextInfo!;
      contextInfo.stanzaId = 'STICKER1';
      contextInfo.participant = 'author@lid';
      return data;
    }

    function stickerMediaHandler(downloadAudio: () => Promise<Buffer>): MediaHandler {
      return {
        detectMedia: vi.fn().mockReturnValue({ type: 'sticker', source: 'quoted' }),
        downloadMedia: vi
          .fn()
          .mockImplementation((_message, source: string) =>
            source === 'quoted' ? Promise.resolve(sticker) : downloadAudio(),
          ),
      } as unknown as MediaHandler;
    }

    it('inlines the stored audio of the quoted sticker', async () => {
      const broker = makeBroker();
      const mediaHandler = stickerMediaHandler(() => Promise.resolve(sound));
      const data = quotingSticker();

      await new CommandPublisher(broker, mediaHandler, audioStore(audio)).publish(data);

      expect(publishedEnvelope(broker).data.media_audio_b64).toBe(sound.toString('base64'));
    });

    it('downloads the audio under the quoted message key', async () => {
      const broker = makeBroker();
      const mediaHandler = stickerMediaHandler(() => Promise.resolve(sound));
      const data = quotingSticker();

      await new CommandPublisher(broker, mediaHandler, audioStore(audio)).publish(data);

      expect(mediaHandler.downloadMedia).toHaveBeenCalledWith(
        {
          key: { remoteJid: data.key.remoteJid, id: 'STICKER1', participant: 'author@lid' },
          message: { audioMessage: audio },
        },
        'direct',
      );
    });

    it('looks the audio up by chat and quoted message id', async () => {
      const store = audioStore(audio);
      const data = quotingSticker();

      await new CommandPublisher(
        makeBroker(),
        stickerMediaHandler(() => Promise.resolve(sound)),
        store,
      ).publish(data);

      expect(store.find).toHaveBeenCalledWith(data.key.remoteJid, 'STICKER1');
    });

    it('publishes a silent sticker when no audio is stored', async () => {
      const broker = makeBroker();
      const mediaHandler = stickerMediaHandler(() => Promise.resolve(sound));

      await new CommandPublisher(broker, mediaHandler, audioStore()).publish(quotingSticker());

      const envelope = publishedEnvelope(broker);
      expect(envelope.data.media_buffer_b64).toBe(sticker.toString('base64'));
      expect(envelope.data.media_audio_b64).toBeUndefined();
    });

    it('publishes a silent sticker when the audio download fails', async () => {
      const broker = makeBroker();
      const mediaHandler = stickerMediaHandler(() => Promise.reject(new Error('expired')));

      await new CommandPublisher(broker, mediaHandler, audioStore(audio)).publish(quotingSticker());

      const envelope = publishedEnvelope(broker);
      expect(envelope.data.media_buffer_b64).toBe(sticker.toString('base64'));
      expect(envelope.data.media_audio_b64).toBeUndefined();
    });

    it('skips the lookup for media other than a sticker', async () => {
      const store = audioStore(audio);
      const mediaHandler = {
        detectMedia: vi.fn().mockReturnValue({ type: 'image', source: 'quoted' }),
        downloadMedia: vi.fn().mockResolvedValue(sticker),
      } as unknown as MediaHandler;

      await new CommandPublisher(makeBroker(), mediaHandler, store).publish(quotingSticker());

      expect(store.find).not.toHaveBeenCalled();
    });
  });
});
