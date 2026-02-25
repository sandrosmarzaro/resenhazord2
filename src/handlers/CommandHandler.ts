import type { WAMessage } from '@whiskeysockets/baileys';
import type { CommandData } from '../types/command.js';
import { promises as fs } from 'fs';
import { fileURLToPath } from 'url';
import path from 'path';
import GetTextMessage from '../utils/GetTextMessage.js';
import ReactMessage from '../utils/ReactMessage.js';
import GetGroupExpiration from '../utils/GetGroupExpiration.js';
import AdmCommand from '../commands/AdmCommand.js';

interface Command {
  identifier: string;
  run: (data: CommandData) => Promise<void>;
}

export default class CommandHandler {
  static async run(data: WAMessage): Promise<void> {
    const text = GetTextMessage.run(data);
    const handler = await this.import_comands();

    for (const [identifier, command] of Object.entries(handler)) {
      if (new RegExp(identifier, 'i').test(text)) {
        await ReactMessage.run(data);
        if (data?.key?.participantAlt == '5528988038529@s.whatsapp.net') {
          await AdmCommand.run({
            ...data,
            text: text,
            expiration: await GetGroupExpiration.run(data),
          } as CommandData);
          return;
        }
        await command.run({
          ...data,
          text: text,
          expiration: await GetGroupExpiration.run(data),
        } as CommandData);
      }
    }
  }

  static async import_comands(): Promise<Record<string, Command>> {
    const __filename = fileURLToPath(import.meta.url);
    const __dirname = path.dirname(__filename);
    const commands_dir = path.resolve(__dirname, '../commands');
    const files = (await fs.readdir(commands_dir)).filter((f) => f.endsWith('.ts'));
    const handler: Record<string, Command> = {};

    for (const file of files) {
      const { default: Command } = (await import(`../commands/${file}`)) as { default: Command };
      handler[Command.identifier] = Command;
    }

    return handler;
  }
}
