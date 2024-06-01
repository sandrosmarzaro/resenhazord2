import request_pkg from 'request';
const request = request_pkg;
import pkg from 'whatsapp-web.js';
const { MessageMedia } = pkg;

export default class PokemonCommand {

    static identifier = "^\\s*\\,\\s*pok.mon\\s*$";

    static async run(data) {
        console.log('POKEMON COMMAND');

        const chat = await data.getChat();
        const url = 'https://pokeapi.co/api/v2/pokemon/';
        const pokemon_id = Math.floor(Math.random() * 1025) + 1;
        request(`${url}${pokemon_id}`, (error, response, body) => {
            if (error) {
                console.error('POKEMON COMMAND ERROR', error);
                return;
            }
            const pokemon = JSON.parse(body);
            const types = pokemon.types.map(({ type }) => type.name);
            const poke_caption = `Nome: ${pokemon.name}\nTipo: ${types.join(', ')}\nPokédex: #${pokemon.id}`;
            let poke_image_url;
            if (pokemon.sprites.other['official-artwork'].front_default) {
                poke_image_url = pokemon.sprites.other['official-artwork'].front_default;
            }
            else {
                poke_image_url = pokemon.sprites.front_default;
            }
            console.log('pokemon', poke_image_url);
            (async () => {
                chat.sendMessage(
                    await MessageMedia.fromUrl(poke_image_url),
                    {
                        sendSeen: true,
                        isViewOnce: true,
                        caption: poke_caption,
                        quotedMessageId: data.id._serialized,
                    }
                );
            })();
        });
    }
}