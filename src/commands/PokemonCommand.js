import Resenhazord2 from '../models/Resenhazord2.js';
import axios from 'axios';

export default class PokemonCommand {

    static identifier = "^\\s*\\,\\s*pok.mon\\s*(?:show)?\\s*(?:dm)?$";

    static async run(data) {

        const url = 'https://pokeapi.co/api/v2/pokemon/';
        const pokemon_id = Math.floor(Math.random() * 1025) + 1;
        await axios.get(`${url}${pokemon_id}`)
            .then(async response => {
                const pokemon = response.data;
                const poke_name = `*Nome*: ${pokemon.name.charAt(0).toUpperCase() + pokemon.name.slice(1)}\n`;
                const typeEmojis = {
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
                    fairy: '🧚'
                };
                const types = pokemon.types.map(({ type }) => typeEmojis[type.name] || type.name);
                const poke_type = `*Tipo*: ${types.join(' ')}\n`
                const poke_dex = `*Pokédex*: #${pokemon.id}`
                const poke_caption = poke_name + poke_type + poke_dex
                let poke_image_url;
                if (pokemon.sprites.other['official-artwork'].front_default) {
                    poke_image_url = pokemon.sprites.other['official-artwork'].front_default;
                }
                else {
                    poke_image_url = pokemon.sprites.front_default;
                }

                let chat_id = data.key.remoteJid
                const DM_FLAG_ACTIVE = data.text.match(/dm/)
                if (DM_FLAG_ACTIVE && data.key.participant) {
                    chat_id = data.key.participant
                }
                await Resenhazord2.socket.sendMessage(
                    chat_id,
                    {
                        viewOnce: !(data.text.match(/show/)),
                        caption: poke_caption,
                        image: { url: poke_image_url },
                    },
                    { quoted: data, ephemeralExpiration: data.expiration }
                );
            })
            .catch(async error => {
                console.log(`POKEMON COMMAND ERROR\n${error}`);
                await Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    { text: 'Viiixxiii... Não consegui baixar o pokémon! 🥺👉👈' },
                    { quoted: data, ephemeralExpiration: data.expiration }
                );
            });
    }
}