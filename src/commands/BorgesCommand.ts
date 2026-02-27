import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import { MongoClient } from 'mongodb';

export default class BorgesCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*borges\\s*$';
  readonly menuDescription = 'Descubra quantos nargas o Borges já fumou.';

  async run(data: CommandData): Promise<Message[]> {
    const uri = process.env.MONGODB_URI!;
    const client = new MongoClient(uri);

    try {
      await client.connect();
      const database = client.db('resenhazord2');
      const collection = database.collection<{ _id: string; nargas: number }>('borges');
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
    } finally {
      await client.close();
    }
  }
}
