import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import axios from 'axios';

export default class PokemonCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*pok.mon\\s*(?:show)?\\s*(?:dm)?$';
  readonly menuDescription = 'Receba uma imagem e dados de um pokémon aleatório.';

  async run(data: CommandData): Promise<Message[]> {
    const url = 'https://pokeapi.co/api/v2/pokemon/';
    const pokemon_id = Math.floor(Math.random() * 1025) + 1;
    const response = await axios.get(`${url}${pokemon_id}`);
    const pokemon = response.data;
    const poke_name = `*Nome*: ${pokemon.name.charAt(0).toUpperCase() + pokemon.name.slice(1)}\n`;
    const typeEmojis: Record<string, string> = {
      normal: '👤',
      fire: '🔥',
      water: '💦',
      electric: '⚡',
      grass: '🍃',
      ice: '❄️',
      fighting: '🥊',
      poison: '☠️',
      ground: '⛰️',
      flying: '🪽',
      psychic: '🔮',
      bug: '🪲',
      rock: '🪨',
      ghost: '👻',
      dragon: '🐉',
      dark: '🌑',
      steel: '⛓️',
      fairy: '🧚',
    };
    const types = pokemon.types.map(
      ({ type }: { type: { name: string } }) => typeEmojis[type.name] || type.name,
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

    let chat_id: string = data.key.remoteJid!;
    const DM_FLAG_ACTIVE = data.text.match(/dm/);
    if (DM_FLAG_ACTIVE && data.key.participant) {
      chat_id = data.key.participant;
    }
    return [
      {
        jid: chat_id,
        content: {
          viewOnce: !data.text.match(/show/),
          caption: poke_caption,
          image: { url: poke_image_url },
        },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }
}
