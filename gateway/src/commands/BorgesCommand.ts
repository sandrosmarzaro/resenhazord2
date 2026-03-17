import Command, {
  type CommandData,
  type CommandConfig,
  type ParsedCommand,
  type Message,
} from './Command.js';
import MongoDBConnection from '../infra/MongoDBConnection.js';
import Reply from '../builders/Reply.js';

export default class BorgesCommand extends Command {
  readonly config: CommandConfig = { name: 'borges', category: 'outras' };
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
    return [Reply.to(data).text(`Borges já fumou ${result!.nargas} nargas 🚬`)];
  }
}
