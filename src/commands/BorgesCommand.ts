import type { CommandData } from '../types/command.js';
import Resenhazord2 from '../models/Resenhazord2.js';
import { MongoClient } from 'mongodb';

export default class BorgesCommand {
  static identifier: string = '^\\s*\\,\\s*borges\\s*$';

  static async run(data: CommandData): Promise<void> {
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
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `Borges já fumou ${result!.nargas} nargas 🚬` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
    } catch (error) {
      console.log(`BORGES COMMAND ERROR\n${error}`);
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: 'Eram muitas bitucas para contar e não consegui... 😔' },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
    } finally {
      await client.close();
    }
  }
}
