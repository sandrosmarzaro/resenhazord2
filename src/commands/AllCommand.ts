import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import { ArgType } from '../types/commandConfig.js';
import Command from './Command.js';
import Reply from '../builders/Reply.js';

export default class AllCommand extends Command {
  readonly config: CommandConfig = { name: 'all', args: ArgType.Optional, groupOnly: true };
  readonly menuDescription = 'Marca todos os participantes do grupo com ou sem uma mensagem.';

  protected async execute(data: CommandData, parsed: ParsedCommand): Promise<Message[]> {
    const { participants } = await this.whatsapp!.groupMetadata(data.key.remoteJid!);
    const text_inserted = parsed.rest.trim();
    let message = text_inserted.length > 0 ? text_inserted : '';
    message += '\n\n';
    const regex = /@lid|@s.whatsapp.net/gi;
    for (const participant of participants) {
      message += `@${participant.id.replace(regex, '')} `;
    }
    const participants_ids = participants.map((participant) => participant.id);
    return [Reply.to(data).textWith(message, participants_ids)];
  }
}
