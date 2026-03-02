import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
// @ts-expect-error - plain JS data files without type declarations
import menu_message from '../../public/messages/menu_message.js';
// @ts-expect-error - plain JS data files without type declarations
import menu_grupo_message from '../../public/messages/menu_grupo_message.js';
// @ts-expect-error - plain JS data files without type declarations
import menu_biblia_message from '../../public/messages/menu_biblia_message.js';

export default class MenuCommand extends Command {
  readonly config: CommandConfig = {
    name: 'menu',
    options: [{ name: 'section', values: ['grupo', 'bíblia'] }],
    flags: ['dm'],
  };
  readonly menuDescription = 'Exibe o menu de comandos.';

  protected async execute(data: CommandData, parsed: ParsedCommand): Promise<Message[]> {
    const section = parsed.options.get('section');
    let menu: string;

    if (section === 'grupo') {
      menu = menu_grupo_message as string;
    } else if (section === 'bíblia') {
      menu = menu_biblia_message as string;
    } else {
      menu = menu_message as string;
    }

    return [
      {
        jid: data.key.remoteJid!,
        content: { text: menu },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }
}
