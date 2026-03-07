import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import { ArgType } from '../types/commandConfig.js';
import Command from './Command.js';
import Reply from '../builders/Reply.js';

export default class MediaCommand extends Command {
  readonly config: CommandConfig = { name: 'media', args: ArgType.Optional };
  readonly menuDescription = 'Baixe o vídeo do link especificado de várias redes sociais.';

  protected async execute(data: CommandData, parsed: ParsedCommand): Promise<Message[]> {
    const url = parsed.rest.trim();
    if (url.length === 0) {
      return [Reply.to(data).text('Me passa o link do vídeo que você quer baixar 🤗')];
    }
    return [Reply.to(data).text(`Viiixxiii... Não consegui baixar o vídeo! 🥺👉👈`)];
  }
}
