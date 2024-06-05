import Resenhazord2 from '../models/Resenhazord2.js';
import menu_message from '../../public/messages/menu_message.js'

export default class MenuCommand {

    static identifier = "^\\s*\\,\\s*menu\\s*$";

    static async run(data) {
        console.log('MENU COMMAND');

        const menu = menu_message;
        try {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: menu},
                {quoted: data}
            );
        }
        catch (error) {
            console.error('ERROR MENU COMMAND', error);
        }
    }
}