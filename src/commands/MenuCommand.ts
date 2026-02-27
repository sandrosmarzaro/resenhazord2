import type { CommandData } from '../types/command.js';
import Command from './Command.js';
import Resenhazord2 from '../models/Resenhazord2.js';
// @ts-expect-error - plain JS data files without type declarations
import menu_message from '../../public/messages/menu_message.js';
// @ts-expect-error - plain JS data files without type declarations
import menu_grupo_message from '../../public/messages/menu_grupo_message.js';
// @ts-expect-error - plain JS data files without type declarations
import menu_biblia_message from '../../public/messages/menu_biblia_message.js';

export default class MenuCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*menu\\s*(?:grupo|b.blia)?\\s*(?:dm)?$';
  readonly menuDescription = 'Exibe o menu de comandos.';

  async run(data: CommandData): Promise<void> {
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

    try {
      let chat_id: string = data.key.remoteJid!;
      const DM_FLAG_ACTIVE = data.text.match(/dm/);
      if (DM_FLAG_ACTIVE && data.key.participant) {
        chat_id = data.key.participant;
      }
      await Resenhazord2.socket!.sendMessage(
        chat_id,
        { text: menu },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
    } catch (error) {
      console.log(`ERROR MENU COMMAND\n${error}`);
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: 'Viiixxiii.. Não consegui exibir o menu! 🥺👉👈' },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
    }
  }
}
