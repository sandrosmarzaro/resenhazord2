import AddCommand from '../commands/AddCommand.js';
import AdmCommand from '../commands/AdmCommand.js';
import AllCommand from '../commands/AllCommand.js';
import AudioCommand from '../commands/AudioCommand.js';
import BanCommand from '../commands/BanCommand.js';
import FuckCommand from '../commands/FuckCommand.js';
import MateusCommand from '../commands/MateusCommand.js';
import OiCommand from '../commands/OiCommand.js';
import PokemonCommad from '../commands/PokemonCommand.js';
import PornoCommand from '../commands/PornoCommand.js';
import Rule34Command from '../commands/Rule34Command.js';

export default class CommandHandler {

    static async run(data) {
        console.log('COMMAND HANDLER');

        const message = data.body;
        const handler = {
            ["^\\s*\\,\\s*add\\s*(?:\\d+)?\\s*$"]: AddCommand,
            ["^\\s*\\,\\s*adm\\s*$"]: AdmCommand,
            ["^\\s*\\,\\s*all\\s*"]: AllCommand,
            ["^\\s*\\,\\s*.udio\\s*(?:[A-Za-z]{2}\\s*\\-\\s*[A-Za-z]{2})?"]: AudioCommand,
            ["^\\s*\\,\\s*ban\\s*(?:\\@\\d+\\s*)*\\s*$"]: BanCommand,
            ["^\\s*\\,\\s*fuck\\s*(?:\\@\\d+\\s*)$"]: FuckCommand,
            ["^\\s*\\,\\s*mateus\\s*$"]: MateusCommand,
            ["^\\s*\\,\\s*oi\\s*$"]: OiCommand,
            ["^\\s*\\,\\s*pok.mon\\s*$"]: PokemonCommad,
            ["^\\s*\\,\\s*porno\\s*(?:ia)?\\s*$"]: PornoCommand,
            ["^\\s*\\,\\s*rule34\\s*$"]: Rule34Command
        }
        for (const [regex, command] of Object.entries(handler)) {
            if (new RegExp(regex, 'i').test(message)) {
                command.run(data);
            }
        }
    }
}