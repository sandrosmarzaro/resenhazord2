import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import AxiosClient from '../infra/AxiosClient.js';
import Reply from '../builders/Reply.js';
import { POKEMON_TYPE_EMOJIS } from '../data/pokemonTypeEmojis.js';
import { Sentry } from '../infra/Sentry.js';

interface PokemonTCGCard {
  name: string;
  supertype: string;
  subtypes?: string[];
  hp?: string;
  types?: string[];
  rarity?: string;
  artist?: string;
  flavorText?: string;
  number: string;
  images: { small: string; large: string };
  set: { name: string; printedTotal: number };
}

interface PokemonTCGResponse {
  data: PokemonTCGCard[];
  totalCount: number;
}

export default class PokemonTCGCommand extends Command {
  readonly config: CommandConfig = {
    name: 'pokémontcg',
    aliases: ['ptcg'],
    flags: ['show', 'dm'],
    category: 'aleatórias',
  };
  readonly menuDescription = 'Receba uma carta aleatória do Pokémon TCG.';

  private static readonly API_URL = 'https://api.pokemontcg.io/v2/cards';
  private static readonly TIMEOUT = 60000;

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
    const headers = process.env.POKEMON_TCG_API_KEY
      ? { 'X-Api-Key': process.env.POKEMON_TCG_API_KEY }
      : undefined;

    const config = { timeout: PokemonTCGCommand.TIMEOUT, ...(headers ? { headers } : {}) };

    try {
      const countResponse = await AxiosClient.get<PokemonTCGResponse>(
        `${PokemonTCGCommand.API_URL}?pageSize=1`,
        config,
      );
      const totalCount = countResponse.data.totalCount;

      const randomPage = Math.floor(Math.random() * totalCount) + 1;
      const cardResponse = await AxiosClient.get<PokemonTCGResponse>(
        `${PokemonTCGCommand.API_URL}?pageSize=1&page=${randomPage}`,
        config,
      );

      const card = cardResponse.data.data[0];

      if (!card?.images?.large) {
        return [
          Reply.to(data).text('Não foi possível encontrar uma carta com imagem. Tente novamente.'),
        ];
      }

      const caption = this.buildCaption(card);
      return [Reply.to(data).image(card.images.large, caption)];
    } catch (error) {
      Sentry.captureException(error, { extra: { command: 'pokemontcg' } });
      return [Reply.to(data).text('Não foi possível buscar uma carta no momento. Tente novamente.')];
    }
  }

  private buildCaption(card: PokemonTCGCard): string {
    const subtypes = card.subtypes?.join(', ') ?? '';
    const typeEmojis =
      card.types?.map((t) => POKEMON_TYPE_EMOJIS[t.toLowerCase()] ?? t).join(' ') ?? '';

    const lines: string[] = [];
    lines.push(`*${card.name}* — ${card.supertype}${subtypes ? ` ${subtypes}` : ''}`);

    const statsLine = [card.hp ? `❤️ HP: ${card.hp}` : '', typeEmojis ? `⚡ ${typeEmojis}` : '']
      .filter(Boolean)
      .join('   ');
    if (statsLine) lines.push(statsLine);

    lines.push('');
    lines.push(`📦 ${card.set.name} #${card.number}/${card.set.printedTotal}`);
    if (card.rarity) lines.push(`⭐ ${card.rarity}`);
    if (card.artist) lines.push(`🎨 ${card.artist}`);
    if (card.flavorText) lines.push(`\n> ${card.flavorText}`);

    return lines.join('\n');
  }
}
