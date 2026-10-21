import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import MessageUpsertEvent from '../../../src/events/MessageUpsertEvent.js';
import CommandHandler from '../../../src/handlers/CommandHandler.js';
import Resenhazord2 from '../../../src/models/Resenhazord2.js';
import logger from '../../../src/infra/Logger.js';
import { createMockWhatsAppPort } from '../../fixtures/factories/MockWhatsAppPort.js';
import { WAMessageFactory } from '../../fixtures/factories/WAMessageFactory.js';
import type WhatsAppPort from '../../../src/ports/WhatsAppPort.js';

describe('MessageUpsertEvent', () => {
  let whatsapp: WhatsAppPort;
  let handleCommand: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    whatsapp = createMockWhatsAppPort({ readMessages: vi.fn().mockResolvedValue(undefined) });
    Resenhazord2.adapter = whatsapp;
    handleCommand = vi.spyOn(CommandHandler, 'run').mockResolvedValue();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('read receipts', () => {
    it('marks every incoming message as read', async () => {
      const group = WAMessageFactory.transient({ isGroup: true }).build();
      const direct = WAMessageFactory.build();

      await MessageUpsertEvent.run({ type: 'notify', messages: [group, direct] });

      expect(whatsapp.readMessages).toHaveBeenCalledWith([group.key, direct.key]);
    });

    it("skips the bot's own messages and status updates", async () => {
      const own = WAMessageFactory.build({ key: { remoteJid: 'u@s.whatsapp.net', fromMe: true } });
      const status = WAMessageFactory.build({ key: { remoteJid: 'status@broadcast' } });

      await MessageUpsertEvent.run({ type: 'notify', messages: [own, status] });

      expect(whatsapp.readMessages).not.toHaveBeenCalled();
    });

    it('leaves history sync unread', async () => {
      await MessageUpsertEvent.run({ type: 'append', messages: [WAMessageFactory.build()] });

      expect(whatsapp.readMessages).not.toHaveBeenCalled();
    });

    it('logs a failed read and still handles the command', async () => {
      const warn = vi.spyOn(logger, 'warn');
      vi.mocked(whatsapp.readMessages).mockRejectedValue(new Error('offline'));
      const message = WAMessageFactory.build();

      await MessageUpsertEvent.run({ type: 'notify', messages: [message] });

      expect(handleCommand).toHaveBeenCalledWith(message);
      await vi.waitFor(() =>
        expect(warn).toHaveBeenCalledWith({
          event: 'read_receipt_failed',
          error: 'Error: offline',
        }),
      );
    });
  });
});
