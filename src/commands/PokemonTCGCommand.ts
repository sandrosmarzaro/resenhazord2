import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import type { BoosterConfig, CardItem } from './CardBoosterCommand.js';
import CardBoosterCommand from './CardBoosterCommand.js';
import AxiosClient from '../infra/AxiosClient.js';
import Reply from '../builders/Reply.js';
import { POKEMON_TYPE_EMOJIS } from '../data/pokemonTypeEmojis.js';
import { Sentry } from '../infra/Sentry.js';

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

export default class PokemonTCGCommand extends CardBoosterCommand {
  readonly config: CommandConfig = {
    name: 'pokémontcg',
    aliases: ['ptcg'],
    flags: ['booster', 'show', 'dm'],
    category: 'aleatórias',
  };
  readonly menuDescription = 'Receba uma carta aleatória do Pokémon TCG.';

  protected readonly boosterConfig: BoosterConfig = {
    flagName: 'booster',
    count: 6,
    columns: 3,
    cellWidth: 300,
    cellHeight: 420,
    shim: 0,
    shimBackground: '#ffffff',
    background: { r: 0, g: 0, b: 0, alpha: 0 },
  };

  private static readonly BASE_URL = 'https://api.tcgdex.net/v2/en';
  private static readonly TIMEOUT = 30000;
  private static readonly MAX_RETRIES = 3;

  protected async execute(data: CommandData, parsed: ParsedCommand): Promise<Message[]> {
    if (parsed.flags.has('booster')) {
      return this.runBooster(data);
    }

    const config = { timeout: PokemonTCGCommand.TIMEOUT, retries: 0 };

    try {
      let card: TCGdexCard | undefined;
      for (let attempt = 0; attempt < PokemonTCGCommand.MAX_RETRIES; attempt++) {
        const response = await AxiosClient.get<TCGdexCard>(
          `${PokemonTCGCommand.BASE_URL}/random/card`,
          config,
        );
        if (response.data.image) {
          card = response.data;
          break;
        }
      }

      if (!card) {
        Sentry.captureMessage('PokemonTCG: no card with image after retries', 'warning');
        return [
          Reply.to(data).text('Não foi possível encontrar uma carta com imagem. Tente novamente.'),
        ];
      }

      const caption = this.buildCaption(card);
      const imageBuffer = await AxiosClient.getBuffer(`${card.image}/high.webp`, config);
      return [Reply.to(data).imageBuffer(imageBuffer, caption)];
    } catch (error) {
      Sentry.captureException(error, { extra: { command: 'pokemontcg' } });
      return [
        Reply.to(data).text('Não foi possível buscar uma carta no momento. Tente novamente.'),
      ];
    }
  }

  protected async fetchBoosterItems(): Promise<CardItem[]> {
    const cards = await Promise.all(
      Array.from({ length: this.boosterConfig.count }, () => this.fetchSingleCard()),
    );
    return cards.map((card) => ({
      imageUrl: `${card.image}/high.webp`,
      label: this.buildBoosterLabel(card),
    }));
  }

  private async fetchSingleCard(): Promise<TCGdexCard> {
    const config = { timeout: PokemonTCGCommand.TIMEOUT, retries: 0 };
    for (let attempt = 0; attempt < PokemonTCGCommand.MAX_RETRIES; attempt++) {
      const response = await AxiosClient.get<TCGdexCard>(
        `${PokemonTCGCommand.BASE_URL}/random/card`,
        config,
      );
      if (response.data.image) return response.data;
    }
    throw new Error('PokemonTCG: no card with image after retries');
  }

  private buildBoosterLabel(card: TCGdexCard): string {
    const typeEmojis =
      card.types?.map((t) => POKEMON_TYPE_EMOJIS[t.toLowerCase()] ?? t).join(' ') ?? '';
    const parts: string[] = [`*${card.name}* -`];
    if (card.rarity) parts.push(`⭐ _${card.rarity}_\n`);
    if (typeEmojis) parts.push(typeEmojis);

    return parts.join(' ');
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
