import Resenhazord2 from '../models/Resenhazord2.js';
import menu_message from '../../public/messages/menu_message.js'
import menu_grupo_message from '../../public/messages/menu_grupo_message.js';

export default class MenuCommand {

    static identifier = "^\\s*\\,\\s*menu\\s*(?:grupo)?\\s*$";

    static async run(data) {
        console.log('MENU COMMAND');

        const menu = data.text.match(/grupo/) ? menu_grupo_message : menu_message;
        try {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: menu},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
        }
        catch (error) {
            console.error('ERROR MENU COMMAND', error);

            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: 'Viiixxiii.. Não consegui exibir o menu! 🥺👉👈'},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
        }
    }
}