import Resenhazord2 from "../models/Resenhazord2.js";

export default class D20Command {

    static identifier = "^\\s*\\,\\s*d20\\s*$";

    static async run (data) {
        console.log('D20 COMMAND');

        const d20 = Math.floor(Math.random() * 20) + 1;
        try {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Aqui está sua rolada: ${d20} 🎲`},
                {quoted: data}
            );
        }
        catch (error) {
            console.error('ERROR D20 COMMAND', error);
        }
    }
}