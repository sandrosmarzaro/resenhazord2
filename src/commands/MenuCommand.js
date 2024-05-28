import menu_message from '../../public/messages/menu_message.js'

export default class MenuCommand {

    static async run(data) {
        console.log('MENU COMMAND');

        const chat = await data.getChat();
        const menu = menu_message;

        chat.sendMessage(
            menu,
            { sendSeen: true, quotedMessageId: data.id._serialized }
        );
    }
}