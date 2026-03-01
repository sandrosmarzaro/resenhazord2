import sharp from 'sharp';
import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
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

export default class PokemonCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*pok.mon\\s*(?:team)?\\s*(?:show)?\\s*(?:dm)?$';
  readonly menuDescription = 'Receba uma imagem e dados de um pokémon aleatório.';

  async run(data: CommandData): Promise<Message[]> {
    if (data.text.match(/team/i)) {
      return this.runTeam(data);
    }
    return this.runSingle(data);
  }

  private async runSingle(data: CommandData): Promise<Message[]> {
    const url = 'https://pokeapi.co/api/v2/pokemon/';
    const pokemon_id = Math.floor(Math.random() * 1025) + 1;
    const response = await AxiosClient.get<PokemonResponse>(`${url}${pokemon_id}`);
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

  private async runTeam(data: CommandData): Promise<Message[]> {
    const url = 'https://pokeapi.co/api/v2/pokemon/';
    const ids = Array.from({ length: 6 }, () => Math.floor(Math.random() * 1025) + 1);

    const responses = await Promise.all(
      ids.map((id) => AxiosClient.get<PokemonResponse>(`${url}${id}`)),
    );
    const pokemons = responses.map((r) => r.data);

    const imageUrls = pokemons.map((p) =>
      p.sprites.other['official-artwork'].front_default
        ? p.sprites.other['official-artwork'].front_default
        : p.sprites.front_default,
    );
    const imageBuffers = await Promise.all(imageUrls.map((u) => AxiosClient.getBuffer(u)));

    const resizedBuffers = await Promise.all(
      imageBuffers.map((buf) =>
        sharp(buf)
          .resize(475, 475, { fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } })
          .png()
          .toBuffer(),
      ),
    );

    const gridBuffer = await sharp(resizedBuffers, {
      join: { across: 3, shim: 8, background: '#ffffff' },
    })
      .png()
      .toBuffer();

    const caption = pokemons
      .map((p, i) => {
        const name = p.name.charAt(0).toUpperCase() + p.name.slice(1);
        const types = p.types
          .map(({ type }) => POKEMON_TYPE_EMOJIS[type.name] || type.name)
          .join(' ');
        return `*${i + 1}.* ${name} ${types} (#${p.id})`;
      })
      .join('\n');

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
          caption,
          image: gridBuffer,
        },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }
}
