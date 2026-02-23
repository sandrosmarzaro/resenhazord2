import Resenhazord2 from '../models/Resenhazord2.js';
import menu_message from '../../public/messages/menu_message.js';
import menu_grupo_message from '../../public/messages/menu_grupo_message.js';
import menu_biblia_message from '../../public/messages/menu_biblia_message.js';

export default class MenuCommand {
  static identifier = '^\\s*\\,\\s*menu\\s*(?:grupo|b.blia)?\\s*(?:dm)?$';

  static async run(data) {
    let menu;
    const menu_handler = {
      grupo: menu_grupo_message,
      biblia: menu_biblia_message,
    };
    for (const key in menu_handler) {
      if (data.text.match(new RegExp(key, 'i'))) {
        menu = menu_handler[key];
        break;
      }
    }
    if (!menu) {
      menu = menu_message;
    }

    try {
      let chat_id = data.key.remoteJid;
      const DM_FLAG_ACTIVE = data.text.match(/dm/);
      if (DM_FLAG_ACTIVE && data.key.participant) {
        chat_id = data.key.participant;
      }
      await Resenhazord2.socket.sendMessage(
        chat_id,
        { text: menu },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
    } catch (error) {
      console.log(`ERROR MENU COMMAND\n${error}`);
      await Resenhazord2.socket.sendMessage(
        data.key.remoteJid,
        { text: 'Viiixxiii.. Não consegui exibir o menu! 🥺👉👈' },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
    }
  }
}
