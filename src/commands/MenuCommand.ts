import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
// @ts-expect-error - plain JS data files without type declarations
import menu_message from '../../public/messages/menu_message.js';
// @ts-expect-error - plain JS data files without type declarations
import menu_grupo_message from '../../public/messages/menu_grupo_message.js';
// @ts-expect-error - plain JS data files without type declarations
import menu_biblia_message from '../../public/messages/menu_biblia_message.js';

export default class MenuCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*menu\\s*(?:grupo|b.blia)?\\s*(?:dm)?$';
  readonly menuDescription = 'Exibe o menu de comandos.';

  async run(data: CommandData): Promise<Message[]> {
    let menu: string;
    const menu_handler: Record<string, string> = {
      grupo: menu_grupo_message as string,
      biblia: menu_biblia_message as string,
    };
    for (const key in menu_handler) {
      if (data.text.match(new RegExp(key, 'i'))) {
        menu = menu_handler[key];
        break;
      }
    }
    if (!menu!) {
      menu = menu_message as string;
    }

    let chat_id: string = data.key.remoteJid!;
    const DM_FLAG_ACTIVE = data.text.match(/dm/);
    if (DM_FLAG_ACTIVE && data.key.participant) {
      chat_id = data.key.participant;
    }
    return [
      {
        jid: chat_id,
        content: { text: menu },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }
}
