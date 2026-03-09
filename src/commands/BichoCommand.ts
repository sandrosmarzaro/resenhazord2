import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import { ArgType } from '../types/commandConfig.js';
import Command from './Command.js';
import BichoScraper from '../services/BichoScraper.js';
import Reply from '../builders/Reply.js';

const ARG_TO_DRAW_ID: Record<string, string> = {
  ppt: 'PPT',
  ptm: 'PTM',
  pt: 'PT',
  ptv: 'PTV',
  ptn: 'PTN',
  cor: 'COR',
};

const PRIZE_EMOJIS = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣'];

export default class BichoCommand extends Command {
  readonly config: CommandConfig = {
    name: 'bicho',
    args: ArgType.Optional,
    argsPattern: /^(?:ppt|ptm|pt|ptv|ptn|cor)?$/i,
    category: 'outras',
  };
  readonly menuDescription = 'Exibe os resultados do Jogo do Bicho do dia.';

  protected async execute(data: CommandData, parsed: ParsedCommand): Promise<Message[]> {
    try {
      const draws = await BichoScraper.fetch();
      const arg = parsed.rest.toLowerCase().trim();

      let draw;
      if (arg) {
        const id = ARG_TO_DRAW_ID[arg];
        draw = draws.find((d) => d.id === id);
      } else {
        const published = draws.filter((d) => d.published);
        draw = published.at(-1);
      }

      if (!draw) {
        return [Reply.to(data).text('Nenhum sorteio publicado ainda hoje. 🎲')];
      }

      if (!draw.published) {
        return [Reply.to(data).text(`Sorteio ${draw.label} ainda não foi publicado. ⏳`)];
      }

      const dateStr = new Date().toLocaleDateString('pt-BR');
      const lines = [
        `🎲 *Jogo do Bicho — ${draw.label}*`,
        `📅 ${dateStr}`,
        '',
        ...draw.prizes.map(
          (p, i) =>
            `${PRIZE_EMOJIS[i] ?? `${i + 1}`}  ${p.milhar} · ${p.emoji} *${p.animal}* (grupo ${p.group})`,
        ),
      ];

      return [Reply.to(data).text(lines.join('\n'))];
    } catch {
      return [
        Reply.to(data).text('Erro ao buscar resultados do Jogo do Bicho. Tente novamente! 🎲'),
      ];
    }
  }
}
