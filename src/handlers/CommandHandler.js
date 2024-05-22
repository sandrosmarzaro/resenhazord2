import OiCommand from '../commands/OiCommand.js';
import MateusCommand from '../commands/MateusCommand.js';

export default class CommandHandler {
    constructor() {}

    static async run(data) {
        const message = data.message.conversation;
        const handler = {
            [/^\s*\,\s*oi\s*$/]: OiCommand,
            [/^\s*\,\s*mateus\s*$/]: MateusCommand
        }
        for (const [regex, command] of Object.entries(handler)) {
            if (new RegExp(regex, 'i').test(message)) {
                command.run(data);
            }
        }
    }
}