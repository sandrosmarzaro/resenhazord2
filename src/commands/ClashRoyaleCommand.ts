import Command, {
  type CommandData,
  type CommandConfig,
  type ParsedCommand,
  type Message,
} from './Command.js';
import AxiosClient from '../infra/AxiosClient.js';
import Reply from '../builders/Reply.js';

const CARDS_URL = 'https://royaleapi.github.io/cr-api-data/json/cards.json';
const ASSETS_BASE = 'https://raw.githubusercontent.com/RoyaleAPI/cr-api-assets/master/cards/';

const RARITY_EMOJIS: Record<string, string> = {
  Common: '⚪',
  Rare: '🔵',
  Epic: '🟣',
  Legendary: '🟡',
  Champion: '💎',
};

const TYPE_EMOJIS: Record<string, string> = {
  Troop: '🗡️',
  Spell: '🔮',
  Building: '🏗️',
};

interface CRCard {
  key: string;
  name: string;
  elixir: number;
  type: string;
  rarity: string;
  arena: number;
  description: string;
}

export default class ClashRoyaleCommand extends Command {
  readonly config: CommandConfig = { name: 'cr', flags: ['show', 'dm'], category: 'aleatórias' };
  readonly menuDescription = 'Receba uma carta aleatória de Clash Royale.';

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
    try {
      const response = await AxiosClient.get<CRCard[]>(CARDS_URL);
      const cards = response.data;
      const card = cards[Math.floor(Math.random() * cards.length)];

      const imageUrl = `${ASSETS_BASE}${card.key}.png`;
      const rarityEmoji = RARITY_EMOJIS[card.rarity] ?? '❓';
      const typeEmoji = TYPE_EMOJIS[card.type] ?? '❓';

      const lines = [
        `*${card.name}*`,
        '',
        `⚡ ${card.elixir}  •  ${typeEmoji} ${card.type}  •  ${rarityEmoji} ${card.rarity}`,
        `🏟️ Arena ${card.arena}`,
        '',
        `> ${card.description}`,
      ];

      return [Reply.to(data).image(imageUrl, lines.join('\n'))];
    } catch {
      return [
        Reply.to(data).text('Erro ao buscar carta de Clash Royale. Tente novamente mais tarde! ⚔️'),
      ];
    }
  }
}
