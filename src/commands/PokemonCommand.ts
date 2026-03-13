import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import type { BoosterConfig, CardItem } from './CardBoosterCommand.js';
import CardBoosterCommand from './CardBoosterCommand.js';
import Reply from '../builders/Reply.js';
import AxiosClient from '../infra/AxiosClient.js';
import { POKEMON_TYPE_EMOJIS } from '../data/pokemonTypeEmojis.js';

interface PokemonResponse {
  name: string;
  id: number;
  types: { type: { name: string } }[];
  sprites: {
    front_default: string;
    other: { 'official-artwork': { front_default: string | null } };
  };
}

export default class PokemonCommand extends CardBoosterCommand {
  readonly config: CommandConfig = {
    name: 'pokémon',
    flags: ['team', 'show', 'dm'],
    category: 'aleatórias',
  };
  readonly menuDescription = 'Receba uma imagem e dados de um pokémon aleatório.';

  protected readonly boosterConfig: BoosterConfig = {
    flagName: 'team',
    count: 6,
    columns: 3,
    cellWidth: 475,
    cellHeight: 475,
    shim: 0,
    shimBackground: '#ffffff',
    background: { r: 0, g: 0, b: 0, alpha: 0 },
  };

  private static readonly BASE_URL = 'https://pokeapi.co/api/v2/pokemon/';

  protected async execute(data: CommandData, parsed: ParsedCommand): Promise<Message[]> {
    if (parsed.flags.has('team')) {
      return this.runBooster(data);
    }
    return this.runSingle(data);
  }

  protected async fetchBoosterItems(): Promise<CardItem[]> {
    const ids = Array.from(
      { length: this.boosterConfig.count },
      () => Math.floor(Math.random() * 1025) + 1,
    );
    const responses = await Promise.all(
      ids.map((id) => AxiosClient.get<PokemonResponse>(`${PokemonCommand.BASE_URL}${id}`)),
    );
    return responses.map((r) => {
      const p = r.data;
      const name = p.name.charAt(0).toUpperCase() + p.name.slice(1);
      const types = p.types
        .map(({ type }) => POKEMON_TYPE_EMOJIS[type.name] || type.name)
        .join(' ');
      return {
        imageUrl: p.sprites.other['official-artwork'].front_default ?? p.sprites.front_default,
        label: `${name} ${types} (#${p.id})`,
      };
    });
  }

  private async runSingle(data: CommandData): Promise<Message[]> {
    const pokemon_id = Math.floor(Math.random() * 1025) + 1;
    const response = await AxiosClient.get<PokemonResponse>(
      `${PokemonCommand.BASE_URL}${pokemon_id}`,
    );
    const pokemon = response.data;
    const poke_name = `*Nome*: ${pokemon.name.charAt(0).toUpperCase() + pokemon.name.slice(1)}\n`;
    const types = pokemon.types.map(
      ({ type }: { type: { name: string } }) => POKEMON_TYPE_EMOJIS[type.name] || type.name,
    );
    const poke_type = `*Tipo*: ${types.join(' ')}\n`;
    const poke_dex = `*Pokédex*: #${pokemon.id}`;
    const poke_caption = poke_name + poke_type + poke_dex;
    let poke_image_url: string;
    if (pokemon.sprites.other['official-artwork'].front_default) {
      poke_image_url = pokemon.sprites.other['official-artwork'].front_default;
    } else {
      poke_image_url = pokemon.sprites.front_default;
    }
    return [Reply.to(data).image(poke_image_url, poke_caption)];
  }
}
