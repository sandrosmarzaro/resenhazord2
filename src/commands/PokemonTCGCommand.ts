import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import AxiosClient from '../infra/AxiosClient.js';
import Reply from '../builders/Reply.js';
import { POKEMON_TYPE_EMOJIS } from '../data/pokemonTypeEmojis.js';
import { Sentry } from '../infra/Sentry.js';

interface TCGdexSetSummary {
  id: string;
  name: string;
  cardCount: { total: number; official: number };
}

interface TCGdexCardSummary {
  id: string;
  localId: string;
  name: string;
  image?: string;
}

interface TCGdexSetDetail {
  id: string;
  name: string;
  cardCount: { total: number; official: number };
  cards: TCGdexCardSummary[];
}

interface TCGdexCard {
  id: string;
  localId: string;
  name: string;
  category: string;
  image?: string;
  illustrator?: string;
  rarity?: string;
  hp?: number;
  types?: string[];
  stage?: string;
  set: { name: string; cardCount: { total: number; official: number } };
}

export default class PokemonTCGCommand extends Command {
  readonly config: CommandConfig = {
    name: 'pokémontcg',
    aliases: ['ptcg'],
    flags: ['show', 'dm'],
    category: 'aleatórias',
  };
  readonly menuDescription = 'Receba uma carta aleatória do Pokémon TCG.';

  private static readonly BASE_URL = 'https://api.tcgdex.net/v2/en';
  private static readonly TIMEOUT = 15000;

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
    const config = { timeout: PokemonTCGCommand.TIMEOUT };

    try {
      const setsResponse = await AxiosClient.get<TCGdexSetSummary[]>(
        `${PokemonTCGCommand.BASE_URL}/sets`,
        config,
      );
      const sets = setsResponse.data;
      const randomSet = sets[Math.floor(Math.random() * sets.length)];

      const setResponse = await AxiosClient.get<TCGdexSetDetail>(
        `${PokemonTCGCommand.BASE_URL}/sets/${randomSet.id}`,
        config,
      );
      const cardsWithImages = setResponse.data.cards.filter((c) => c.image);

      if (cardsWithImages.length === 0) {
        return [
          Reply.to(data).text('Não foi possível encontrar uma carta com imagem. Tente novamente.'),
        ];
      }

      const randomCardSummary = cardsWithImages[Math.floor(Math.random() * cardsWithImages.length)];

      const cardResponse = await AxiosClient.get<TCGdexCard>(
        `${PokemonTCGCommand.BASE_URL}/cards/${randomCardSummary.id}`,
        config,
      );
      const card = cardResponse.data;

      if (!card.image) {
        return [
          Reply.to(data).text('Não foi possível encontrar uma carta com imagem. Tente novamente.'),
        ];
      }

      const caption = this.buildCaption(card);
      return [Reply.to(data).image(`${card.image}/high.png`, caption)];
    } catch (error) {
      Sentry.captureException(error, { extra: { command: 'pokemontcg' } });
      return [
        Reply.to(data).text('Não foi possível buscar uma carta no momento. Tente novamente.'),
      ];
    }
  }

  private buildCaption(card: TCGdexCard): string {
    const typeEmojis =
      card.types?.map((t) => POKEMON_TYPE_EMOJIS[t.toLowerCase()] ?? t).join(' ') ?? '';

    const lines: string[] = [];
    lines.push(`*${card.name}* — ${card.category}${card.stage ? ` ${card.stage}` : ''}`);

    const statsLine = [card.hp ? `❤️ HP: ${card.hp}` : '', typeEmojis ? `⚡ ${typeEmojis}` : '']
      .filter(Boolean)
      .join('   ');
    if (statsLine) lines.push(statsLine);

    lines.push('');
    lines.push(`📦 ${card.set.name} #${card.localId}/${card.set.cardCount.official}`);
    if (card.rarity) lines.push(`⭐ ${card.rarity}`);
    if (card.illustrator) lines.push(`🎨 ${card.illustrator}`);

    return lines.join('\n');
  }
}
