import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import type { CommandCategory } from '../types/commandConfig.js';
import Command from './Command.js';
import Reply from '../builders/Reply.js';
// @ts-expect-error - plain JS data files without type declarations
import menu_grupo_message from '../../public/messages/menu_grupo_message.js';
// @ts-expect-error - plain JS data files without type declarations
import menu_biblia_message from '../../public/messages/menu_biblia_message.js';
import CommandFactory from '../factories/CommandFactory.js';

const CATEGORY_HEADERS: Record<CommandCategory, string> = {
  grupo: '🫂 FUNÇÕES DE GRUPO 🫂',
  aleatórias: '🎲 FUNÇÕES ALEATÓRIAS 🎲',
  download: '💾 FUNÇÕES DE DOWNLOAD 💾',
  outras: '🙂 OUTRAS FUNÇÕES 🙂',
};

const CATEGORY_ORDER: CommandCategory[] = ['grupo', 'aleatórias', 'download', 'outras'];

export default class MenuCommand extends Command {
  readonly config: CommandConfig = {
    name: 'menu',
    options: [{ name: 'section', values: ['grupo', 'bíblia'] }],
    flags: ['dm'],
    category: 'outras',
  };
  readonly menuDescription = 'Exibe o menu de comandos.';

  protected async execute(data: CommandData, parsed: ParsedCommand): Promise<Message[]> {
    const section = parsed.options.get('section');
    let menu: string;

    if (section === 'grupo') {
      menu = menu_grupo_message as string;
    } else if (section === 'bíblia') {
      menu = menu_biblia_message as string;
    } else {
      menu = this.buildMenu();
    }

    return [Reply.to(data).text(menu)];
  }

  private buildMenu(): string {
    const commands = CommandFactory.getInstance().getAllStrategies();
    const grouped = new Map<CommandCategory, Command[]>();

    for (const cmd of commands) {
      const category = cmd.config.category;
      if (!category) continue;
      if (!grouped.has(category)) grouped.set(category, []);
      grouped.get(category)!.push(cmd);
    }

    const sections: string[] = ['\t\t\t📝 *MENU DE COMANDOS* 📝'];

    for (const category of CATEGORY_ORDER) {
      const cmds = grouped.get(category);
      if (!cmds || cmds.length === 0) continue;

      let header = CATEGORY_HEADERS[category];
      if (category === 'aleatórias') {
        header +=
          '\n\n_(use as opções *show* e/ou *dm* para enviar imagens no chat privado e sem visualização única respectivamente)_';
      }

      const entries = cmds.map((cmd) => {
        const names = [cmd.config.name, ...(cmd.config.aliases ?? [])];
        const namesFormatted = names.map((n) => `*,${n}*`).join(' ou ');
        return `- ${namesFormatted}\n> ${cmd.menuDescription}`;
      });

      sections.push(`${header}\n\n${entries.join('\n\n')}`);
    }

    return sections.join('\n\n');
  }
}
