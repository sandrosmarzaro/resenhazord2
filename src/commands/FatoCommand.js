import Resenhazord2 from "../models/Resenhazord2.js";

export default class FatoCommand {

    static identifier = "^\\s*\\,\\s*fato\\s*(?:hoje)?\\s*$";

    static async run(data) {

        const rest_command = data.text.replace(/\n*\s*\,\s*fato\s*/, '');
        const rest_link = rest_command.match(/hoje/) ? 'today' : 'random';
        let url = `https://uselessfacts.jsph.pl/api/v2/facts/${rest_link}`;

        const response = await fetch(url);
        const fact = await response.json();
        try {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `FATO 🤓☝️\n${fact.text}`},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
        }
        catch (error) {
            Resenhazord2.bugsnag.notify(`ERROR FATO COMMAND\n${error}`);
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: 'Não consegui te dar um fato... 😔'},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
        }

    }
}