import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import CommandParser from '../parsers/CommandParser.js';

export default abstract class Command {
  abstract readonly config: CommandConfig;
  abstract readonly menuDescription: string;

  private _parser?: CommandParser;

  private get parser(): CommandParser {
    if (!this._parser) {
      this._parser = new CommandParser(this.config);
    }
    return this._parser;
  }

  matches(text: string): boolean {
    return this.parser.matches(text);
  }

  async run(data: CommandData): Promise<Message[]> {
    if (this.config.groupOnly && !data.key.remoteJid?.includes('g.us')) {
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: 'Esse comando só funciona em grupo! 🤦‍♂️' },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }
    const parsed = this.parser.parse(data.text);
    const messages = await this.execute(data, parsed);
    return this.applyFlags(data, parsed, messages);
  }

  protected abstract execute(data: CommandData, parsed: ParsedCommand): Promise<Message[]>;

  private applyFlags(data: CommandData, parsed: ParsedCommand, messages: Message[]): Message[] {
    return messages.map((msg) => {
      if (parsed.flags.has('dm') && data.key.participant) {
        msg.jid = data.key.participant;
      }
      if (parsed.flags.has('show') && msg.content && 'viewOnce' in msg.content) {
        (msg.content as Record<string, unknown>).viewOnce = false;
      }
      return msg;
    });
  }
}
