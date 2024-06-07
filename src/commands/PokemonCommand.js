import Resenhazord2 from '../models/Resenhazord2.js';
import axios from 'axios';

export default class PokemonCommand {

    static identifier = "^\\s*\\,\\s*pok.mon\\s*$";

    static async run(data) {
        console.log('POKEMON COMMAND');

        const exp = await Resenhazord2.socket.groupMetadata?.ephemeralDuration ||
                    data.message?.extendedTextMessage?.contextInfo?.expiration;

        const url = 'https://pokeapi.co/api/v2/pokemon/';
        const pokemon_id = Math.floor(Math.random() * 1025) + 1;
        axios.get(`${url}${pokemon_id}`)
            .then(response => {
                const pokemon = response.data;
                const types = pokemon.types.map(({ type }) => type.name);
                const poke_caption = `Nome: ${pokemon.name}\nTipo: ${types.join(', ')}\nPokédex: #${pokemon.id}`;
                let poke_image_url;
                if (pokemon.sprites.other['official-artwork'].front_default) {
                    poke_image_url = pokemon.sprites.other['official-artwork'].front_default;
                } else {
                    poke_image_url = pokemon.sprites.front_default;
                }
                console.log('pokemon', poke_image_url);
                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {
                        viewOnce: true,
                        caption: poke_caption,
                        image: { url: poke_image_url },
                    },
                    { quoted: data, ephemeralExpiration: exp }
                );
            })
            .catch(error => {
                console.error('POKEMON COMMAND ERROR', error);
                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    { text: 'Viiixxiii... Não consegui baixar o pokémon! 🥺👉👈' },
                    { quoted: data, ephemeralExpiration: exp }
                );
            });
    }
}