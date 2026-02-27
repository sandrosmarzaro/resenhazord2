import type { WAMessage } from '@whiskeysockets/baileys';
import type { CommandData } from '../types/command.js';
import type Command from '../commands/Command.js';
import { promises as fs } from 'fs';
import { fileURLToPath } from 'url';
import path from 'path';
import GetTextMessage from '../utils/GetTextMessage.js';
import ReactMessage from '../utils/ReactMessage.js';
import GetGroupExpiration from '../utils/GetGroupExpiration.js';

export default class CommandHandler {
  static commands: Command[] | null = null;

  static async run(data: WAMessage): Promise<void> {
    const text = GetTextMessage.run(data);
    const commands = await this.loadCommands();

    for (const command of commands) {
      if (command.matches(text)) {
        await ReactMessage.run(data);
        if (data?.key?.participantAlt == '5528988038529@s.whatsapp.net') {
          const admCommand = commands.find((c) => c.constructor.name === 'AdmCommand');
          if (admCommand) {
            await admCommand.run({
              ...data,
              text: text,
              expiration: await GetGroupExpiration.run(data),
            } as CommandData);
          }
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

  static async loadCommands(): Promise<Command[]> {
    if (this.commands) return this.commands;

    const __filename = fileURLToPath(import.meta.url);
    const __dirname = path.dirname(__filename);
    const commandsDir = path.resolve(__dirname, '../commands');
    const files = (await fs.readdir(commandsDir)).filter(
      (f) => f.endsWith('.ts') && f !== 'Command.ts',
    );

    this.commands = [];
    for (const file of files) {
      const { default: CommandClass } = await import(`../commands/${file}`);
      this.commands.push(new CommandClass());
    }

    return this.commands;
  }
}
