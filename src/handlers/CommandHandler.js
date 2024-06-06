import { promises as fs } from 'fs';
import { fileURLToPath } from 'url';
import path from 'path';

export default class CommandHandler {

    static async run(data) {
        console.log('COMMAND HANDLER');

        const { text } = data.message?.extendedTextMessage?.text || '';
        const handler = await this.import_comands();

        for (const [identifier, command] of Object.entries(handler)) {
            if (new RegExp(identifier, 'i').test(text)) {
                command.run(data);
            }
        }
    }

    static async import_comands() {
        const __filename = fileURLToPath(import.meta.url);
        const __dirname = path.dirname(__filename);
        const commands_dir = path.resolve(__dirname, '../commands');
        const files = await fs.readdir(commands_dir);
        const handler = {};

        for (const file of files) {
            const { default: Command } = await import(`../commands/${file}`);
            handler[Command.identifier] = Command;
        }

        return handler;
    }
}