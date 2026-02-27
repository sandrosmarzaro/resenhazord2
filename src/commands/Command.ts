import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';

export default abstract class Command {
  abstract readonly regexIdentifier: string;
  abstract readonly menuDescription: string;
  abstract run(data: CommandData): Promise<Message[]>;

  matches(text: string): boolean {
    return new RegExp(this.regexIdentifier, 'i').test(text);
  }
}
