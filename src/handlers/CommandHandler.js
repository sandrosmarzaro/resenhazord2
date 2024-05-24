import OiCommand from '../commands/OiCommand.js';
import MateusCommand from '../commands/MateusCommand.js';
import AddCommand from '../commands/AddCommand.js';

export default class CommandHandler {

    static async run(data) {
        console.log('COMMAND HANDLER');

        const message = data.body;
        const handler = {
            ["^\\s*\\,\\s*oi\\s*$"]: OiCommand,
            ["^\\s*\\,\\s*mateus\\s*$"]: MateusCommand,
            ["^\\s*\\,\\s*add\\s*(?:\\d+)?\\s*$"]: AddCommand
        }
        for (const [regex, command] of Object.entries(handler)) {
            if (new RegExp(regex, 'i').test(message)) {
                command.run(data);
            }
        }
    }
}