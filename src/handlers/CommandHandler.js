import AddCommand from '../commands/AddCommand.js';
import MateusCommand from '../commands/MateusCommand.js';
import Rule34Command from '../commands/Rule34Command.js';
import OiCommand from '../commands/OiCommand.js';

export default class CommandHandler {

    static async run(data) {
        console.log('COMMAND HANDLER');

        const message = data.body;
        const handler = {
            ["^\\s*\\,\\s*add\\s*(?:\\d+)?\\s*$"]: AddCommand,
            ["^\\s*\\,\\s*mateus\\s*$"]: MateusCommand,
            ["^\\s*\\,\\s*rule34\\s*$"]: Rule34Command,
            ["^\\s*\\,\\s*oi\\s*$"]: OiCommand
        }
        for (const [regex, command] of Object.entries(handler)) {
            if (new RegExp(regex, 'i').test(message)) {
                command.run(data);
            }
        }
    }
}