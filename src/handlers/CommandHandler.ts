import type { WAMessage } from '@whiskeysockets/baileys';
import type { CommandData } from '../types/command.js';
import CommandFactory from '../factories/CommandFactory.js';
import GetTextMessage from '../utils/GetTextMessage.js';
import ReactMessage from '../utils/ReactMessage.js';
import GetGroupExpiration from '../utils/GetGroupExpiration.js';

export default class CommandHandler {
  static async run(data: WAMessage): Promise<void> {
    const text = GetTextMessage.run(data);
    const factory = CommandFactory.getInstance();
    const command = factory.getStrategy(text);

    if (command) {
      await ReactMessage.run(data);

      if (data?.key?.participantAlt === '5528988038529@s.whatsapp.net') {
        const admCommand = factory.getStrategy(',adm');
        if (admCommand) {
          await admCommand.run({
            ...data,
            text,
            expiration: await GetGroupExpiration.run(data),
          } as CommandData);
        }
        return;
      }

      await command.run({
        ...data,
        text,
        expiration: await GetGroupExpiration.run(data),
      } as CommandData);
    }
  }
}
