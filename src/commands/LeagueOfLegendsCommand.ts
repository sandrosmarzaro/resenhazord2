import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import DataDragonService from '../services/DataDragonService.js';
import { LOL_ROLE_EMOJIS } from '../data/lolRoleEmojis.js';

export default class LeagueOfLegendsCommand extends Command {
  readonly regexIdentifier = '^\\s*,\\s*lol\\s*(?:show)?\\s*(?:dm)?$';
  readonly menuDescription = 'Receba um campeão aleatório de League of Legends.';

  async run(data: CommandData): Promise<Message[]> {
    let chat_id: string = data.key.remoteJid!;
    const DM_FLAG_ACTIVE = data.text.match(/dm/);
    if (DM_FLAG_ACTIVE && data.key.participant) {
      chat_id = data.key.participant;
    }

    try {
      const champion = await DataDragonService.getRandomChampion();

      const rolesLine = champion.tags.map((tag) => `${LOL_ROLE_EMOJIS[tag] ?? '❓'} ${tag}`).join('  ');

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
          jid: chat_id,
          content: {
            viewOnce: !data.text.match(/show/),
            caption,
            image: { url: champion.splashUrl },
          },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    } catch {
      return [
        {
          jid: chat_id,
          content: { text: 'Erro ao buscar campeão de LoL. Tente novamente mais tarde! 🎮' },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }
  }
}
