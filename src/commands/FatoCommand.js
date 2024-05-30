export default class FatoCommand {

    static identifier = "^\\s*\\,\\s*fato\\s*(?:hoje)?\\s*$";

    static async run(data) {
        console.log('FATO COMMAND');

        const chat = await data.getChat();
        const rest_command = data.body.replace(/\n*\s*\,\s*fato\s*/, '');

        let url = 'https://uselessfacts.jsph.pl/api/v2/facts/';
        const rest_link = rest_command === 'hoje' ? 'today' : 'random';
        url += rest_link;

        const response = await fetch(url);
        const fact = await response.json();
        console.log('fato', fact);
        chat.sendMessage(
            `FATO 🤓☝️\n${fact.text}`,
            { sendSeen: true, quotedMessageId: data.id._serialized }
        );
    }
}