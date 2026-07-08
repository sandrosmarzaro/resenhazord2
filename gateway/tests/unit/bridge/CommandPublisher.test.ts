import { describe, it, expect, vi } from 'vitest';

import CommandPublisher from '../../../src/bridge/CommandPublisher.js';
import type BrokerPort from '../../../src/ports/BrokerPort.js';
import type MediaHandler from '../../../src/bridge/MediaHandler.js';
import { createMockBrokerPort } from '../../fixtures/factories/MockBrokerPort.js';
import { GroupCommandData } from '../../fixtures/index.js';

function makeBroker(): BrokerPort {
  return createMockBrokerPort();
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

      const id = await new CommandPublisher(broker, mediaHandler).publish(data);

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

    it('carries mentions and the quoted text', async () => {
      const broker = makeBroker();
      const mediaHandler = {
        detectMedia: vi.fn().mockReturnValue(null),
      } as unknown as MediaHandler;
      const data = GroupCommandData.build(
        { text: ',ban' },
        { transient: { isGroup: true, mentionedJids: ['victim@s'], hasQuotedMessage: true } },
      );

      await new CommandPublisher(broker, mediaHandler).publish(data);

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

      await new CommandPublisher(broker, mediaHandler).publish(data);

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

      await new CommandPublisher(broker, mediaHandler).publish(data);

      const envelope = publishedEnvelope(broker);
      expect(envelope.data.sender_jid).toBe('5528999223882@s.whatsapp.net');
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

      await new CommandPublisher(broker, mediaHandler).publish(data);

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

      await new CommandPublisher(broker, mediaHandler).publish(data);

      const envelope = publishedEnvelope(broker);
      expect(envelope.data.media_type).toBe('image');
      expect(envelope.data.media_buffer_b64).toBeUndefined();
    });
  });
});
