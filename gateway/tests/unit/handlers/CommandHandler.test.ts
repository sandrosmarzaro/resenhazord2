import { describe, it, expect, vi, afterEach } from 'vitest';
import type { WAMessage } from '@whiskeysockets/baileys';
import CommandHandler from '../../../src/handlers/CommandHandler.js';
import Resenhazord2 from '../../../src/models/Resenhazord2.js';
import { WAMessageFactory } from '../../fixtures/factories/WAMessageFactory.js';

vi.mock('../../../src/factories/CommandFactory.js', () => ({
  default: { getInstance: () => ({ getStrategy: () => null }) },
}));

vi.mock('../../../src/infra/Logger.js', () => ({
  default: { debug: vi.fn(), warn: vi.fn() },
}));

import logger from '../../../src/infra/Logger.js';

function createGroupMessage(text: string): WAMessage {
  const msg = WAMessageFactory.build({}, { transient: { isGroup: true } });
  msg.message = { extendedTextMessage: { text } };
  return msg;
}

function createTextlessDirectMessage(): WAMessage {
  const msg = WAMessageFactory.build();
  msg.key.participant = '';
  msg.message = { messageContextInfo: {} };
  msg.messageStubType = 2;
  msg.messageStubParameters = ['No matching sessions found for message'];
  return msg;
}

afterEach(() => {
  vi.restoreAllMocks();
  Resenhazord2.brokerForwarder = null;
});

describe('CommandHandler', () => {
  describe('broker routing', () => {
    it('forwards a command through the broker forwarder', async () => {
      const forward = vi.fn().mockResolvedValue(undefined);
      Resenhazord2.brokerForwarder = { forward } as never;

      await CommandHandler.run(createGroupMessage(',ping'));

      expect(forward).toHaveBeenCalledWith(expect.anything(), ',ping');
    });

    it('does not throw when the broker is unavailable', async () => {
      Resenhazord2.brokerForwarder = null;

      await expect(CommandHandler.run(createGroupMessage(',ping'))).resolves.toBeUndefined();
    });

    it('does not forward ordinary group chatter', async () => {
      const forward = vi.fn();
      Resenhazord2.brokerForwarder = { forward } as never;

      await CommandHandler.run(createGroupMessage('just chatting'));

      expect(forward).not.toHaveBeenCalled();
    });

    it('ignores messages the bot itself sent, to avoid replying to its own replies', async () => {
      const forward = vi.fn();
      Resenhazord2.brokerForwarder = { forward } as never;

      const ownMessage = createGroupMessage(',ping');
      ownMessage.key.fromMe = true;

      await CommandHandler.run(ownMessage);

      expect(forward).not.toHaveBeenCalled();
    });
  });

  describe('direct messages without text', () => {
    it('does not wake the agent for a DM whose text could not be extracted', async () => {
      const forward = vi.fn();
      Resenhazord2.brokerForwarder = { forward } as never;

      await CommandHandler.run(createTextlessDirectMessage());

      expect(forward).not.toHaveBeenCalled();
    });

    it('logs the message shape so the missing text can be diagnosed', async () => {
      Resenhazord2.brokerForwarder = { forward: vi.fn() } as never;

      await CommandHandler.run(createTextlessDirectMessage());

      expect(logger.warn).toHaveBeenCalledWith({
        event: 'dm_without_text',
        messageTypes: ['messageContextInfo'],
        stubType: 2,
        stubParameters: ['No matching sessions found for message'],
        participant: '',
      });
    });

    it('still forwards a DM carrying media without a caption', async () => {
      const forward = vi.fn().mockResolvedValue(undefined);
      Resenhazord2.brokerForwarder = { forward } as never;

      await CommandHandler.run(
        WAMessageFactory.build({}, { transient: { hasImageMessage: true } }),
      );

      expect(forward).toHaveBeenCalledWith(expect.anything(), '');
    });
  });
});
