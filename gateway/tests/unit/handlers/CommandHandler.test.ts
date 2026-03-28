import type { Mock } from 'vitest';
import type { WAMessage } from '@whiskeysockets/baileys';
import type { Message } from '../../../src/types/message.js';
import CommandHandler from '../../../src/handlers/CommandHandler.js';
import Resenhazord2 from '../../../src/models/Resenhazord2.js';
import TypingIndicator from '../../../src/utils/TypingIndicator.js';
import { WAMessageFactory } from '../../fixtures/factories/WAMessageFactory.js';

vi.mock('../../../src/utils/ReactMessage.js', () => ({
  default: { run: vi.fn() },
}));

vi.mock('../../../src/utils/TypingIndicator.js', () => ({
  default: { start: vi.fn(), stop: vi.fn() },
}));

vi.mock('../../../src/utils/GetGroupExpiration.js', () => ({
  default: { run: vi.fn().mockResolvedValue(undefined) },
}));

vi.mock('../../../src/factories/CommandFactory.js', () => ({
  default: { getInstance: () => ({ getStrategy: () => null }) },
}));

function createGroupMessage(text: string): WAMessage {
  const msg = WAMessageFactory.build({}, { transient: { isGroup: true } });
  msg.message = { extendedTextMessage: { text } };
  return msg;
}

function mockBridge(sendCommand: Mock): void {
  Resenhazord2.bridge = { isConnected: true, sendCommand } as never;
}

function mockBridgeWithAck(messages: Message[] | null): Mock {
  const sendCommand = vi.fn(async (_data: unknown, onAck?: () => Promise<void>) => {
    if (onAck && messages) await onAck();
    return messages;
  });
  mockBridge(sendCommand);
  return sendCommand;
}

function mockAdapter(sendMessage: Mock): void {
  Resenhazord2.adapter = { sendMessage, sendPresenceUpdate: vi.fn() } as never;
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('CommandHandler', () => {
  describe('Python command sendMessages error handling', () => {
    it('sends error message to user when sendMessages throws', async () => {
      const jid = 'group@g.us';
      const messages: Message[] = [{ jid, content: { image: Buffer.alloc(0) } as never }];

      mockBridgeWithAck(messages);

      const sendMessage = vi
        .fn()
        .mockRejectedValueOnce(new Error('Upload failed')) // sendMessages
        .mockResolvedValueOnce(undefined); // error message to user
      mockAdapter(sendMessage);

      const data = createGroupMessage(',ptcg');
      await CommandHandler.run(data);

      const errorCall = sendMessage.mock.calls.find(
        (c) => typeof (c[1] as Record<string, unknown>)?.text === 'string',
      );
      expect(errorCall).toBeDefined();
      expect((errorCall![1] as Record<string, string>).text).toContain('erro');
    });

    it('stops typing indicator even when sendMessages throws', async () => {
      const jid = 'group@g.us';
      const messages: Message[] = [{ jid, content: { text: 'hello' } }];

      mockBridgeWithAck(messages);

      const sendMessage = vi
        .fn()
        .mockRejectedValueOnce(new Error('Send failed')) // sendMessages
        .mockResolvedValueOnce(undefined); // error message
      mockAdapter(sendMessage);

      const data = createGroupMessage(',test');
      await CommandHandler.run(data);

      expect(TypingIndicator.stop).toHaveBeenCalled();
    });

    it('does not throw unhandled errors on sendMessages failure', async () => {
      const jid = 'group@g.us';
      const messages: Message[] = [{ jid, content: { image: Buffer.alloc(0) } as never }];

      mockBridgeWithAck(messages);

      const sendMessage = vi
        .fn()
        .mockRejectedValueOnce(new Error('Baileys crash')) // sendMessages
        .mockResolvedValueOnce(undefined); // error message
      mockAdapter(sendMessage);

      const data = createGroupMessage(',ptcg');

      await expect(CommandHandler.run(data)).resolves.toBeUndefined();
    });
  });
});
