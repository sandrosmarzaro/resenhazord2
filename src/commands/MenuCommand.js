import Resenhazord2 from '../models/Resenhazord2.js';
import menu_message from '../../public/messages/menu_message.js'
import menu_grupo_message from '../../public/messages/menu_grupo_message.js';
import menu_biblia_message from '../../public/messages/menu_biblia_message.js';

export default class MenuCommand {

    static identifier = "^\\s*\\,\\s*menu\\s*(?:grupo|b.blia)?\\s*$";

    static async run(data) {

        let menu;
        const menu_handler = {
            grupo: menu_grupo_message,
            biblia: menu_biblia_message
        };
        for (let key in menu_handler) {
            if (data.text.match(new RegExp(key, 'i'))) {
                menu = menu_handler[key];
                break;
            }
        }
        if (!menu) {
            menu = menu_message;
        }

        try {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: menu},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
        }
        catch (error) {
            console.log(`ERROR MENU COMMAND\n${error}`);
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: 'Viiixxiii.. Não consegui exibir o menu! 🥺👉👈'},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
        }
    }
}