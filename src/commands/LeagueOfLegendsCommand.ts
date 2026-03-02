import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import DataDragonService from '../services/DataDragonService.js';
import { LOL_ROLE_EMOJIS } from '../data/lolRoleEmojis.js';

export default class LeagueOfLegendsCommand extends Command {
  readonly config: CommandConfig = { name: 'lol', flags: ['show', 'dm'] };
  readonly menuDescription = 'Receba um campeão aleatório de League of Legends.';

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
    try {
      const champion = await DataDragonService.getRandomChampion();

      const rolesLine = champion.tags
        .map((tag) => `${LOL_ROLE_EMOJIS[tag] ?? '❓'} ${tag}`)
        .join('  ');

      const lines = [
        `*${champion.name}*`,
        `_${champion.title}_`,
        '',
        rolesLine,
        '',
        `⚔️ Ataque: ${champion.info.attack}/10`,
        `🛡️ Defesa: ${champion.info.defense}/10`,
        `🔮 Magia: ${champion.info.magic}/10`,
        `🎯 Dificuldade: ${champion.info.difficulty}/10`,
        '',
        `> ${champion.blurb}`,
      ];

      const caption = lines.join('\n');

      return [
        {
          jid: data.key.remoteJid!,
          content: {
            viewOnce: true,
            caption,
            image: { url: champion.splashUrl },
          },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    } catch {
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: 'Erro ao buscar campeão de LoL. Tente novamente mais tarde! 🎮' },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }
  }
}
