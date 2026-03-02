import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import MongoDBConnection from '../infra/MongoDBConnection.js';

export default class BorgesCommand extends Command {
  readonly config: CommandConfig = { name: 'borges' };
  readonly menuDescription = 'Descubra quantos nargas o Borges já fumou.';

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
    const collection = await MongoDBConnection.getCollection<{ _id: string; nargas: number }>(
      'borges',
    );
    const result = await collection.findOneAndUpdate(
      { _id: 'counter' },
      { $inc: { nargas: 1 } },
      { returnDocument: 'after', upsert: true },
    );
    return [
      {
        jid: data.key.remoteJid!,
        content: { text: `Borges já fumou ${result!.nargas} nargas 🚬` },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }
}
