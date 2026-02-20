import { promises as fs } from 'fs';
import { fileURLToPath } from 'url';
import path from 'path';
import GetTextMessage from '../utils/GetTextMessage.js';
import ReactMessage from '../utils/ReactMessage.js';
import GetGroupExpiration from '../utils/GetGroupExpiration.js';
import AdmCommand from '../commands/AdmCommand.js';

export default class CommandHandler {

  static async run(data) {
    const text = GetTextMessage.run(data);
    const handler = await this.import_comands();

    for (const [identifier, command] of Object.entries(handler)) {
      if (new RegExp(identifier, 'i').test(text)) {
        await ReactMessage.run(data);
        {
          if (data?.key?.participantAlt == "5528988038529@s.whatsapp.net") {
            await AdmCommand.run({ ...data, text: text, expiration: await GetGroupExpiration.run(data) });
            return;
          }
          await command.run({
            ...data,
            text: text,
            expiration: await GetGroupExpiration.run(data)
          });
        }
      }
    }
  }

  static async import_comands() {
    const __filename = fileURLToPath(import.meta.url);
    const __dirname = path.dirname(__filename);
    const commands_dir = path.resolve(__dirname, '../commands');
    const files = await fs.readdir(commands_dir);
    const handler = {};

    for (const file of files) {
      const { default: Command } = await import(`../commands/${file}`);
      handler[Command.identifier] = Command;
    }

    return handler;
  }
}