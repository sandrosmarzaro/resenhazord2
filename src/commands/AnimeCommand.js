import Resenhazord2 from '../models/Resenhazord2.js';
import axios from 'axios';

export default class AnimeCommand {

    static identifier = "^\\s*\\,\\s*anime\\s*(?:nsfw|sfw)?\\s*$";

    static async run(data) {
        console.log('ANIME COMMAND');

        const sfw_tags = [
            'waifu', 'neko', 'shinobu', 'megumin', 'bully', 'cuddle', 'cry', 'hug', 'awoo', 'kiss', 'lick',
            'pat', 'smug', 'bonk', 'yeet', 'blush', 'smile', 'wave', 'highfive', 'handhold', 'nom', 'bite',
            'glomp', 'slap', 'kill', 'kick', 'happy', 'wink', 'poke', 'dance', 'cringe'
        ];
        const nsfw_tags = ['waifu', 'neko', 'trap', 'blowjob'];

        const rest_command = data.message.extendedTextMessage.text.replace(/^\s*\,\s*anime\s*/, '');
        const is_nsfw = rest_command.match(/nsfw/);

        let tag;
        is_nsfw ? tag = nsfw_tags[Math.floor(Math.random() * nsfw_tags.length)] : tag = sfw_tags[Math.floor(Math.random() * sfw_tags.length)];
        let type;
        is_nsfw ? type = 'nsfw' : type = 'sfw';

        const url = `https://api.waifu.pics/${type}/${tag}`;
        axios.get(url)
            .then(response => {
                const anime = response.data;
                console.log('anime', anime);
                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {
                        viewOnce: true,
                        video: {url: anime.url},
                        caption: `Aqui está uma foto de anime para você! 😊`
                    },
                    {quoted: data}
                );
            })
            .catch(error => {
                console.error('ERROR ANIME COMMAND', error);
                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {text: 'Viiixxiii... Não consegui baixar a foto! 🥺👉👈'},
                    {quoted: data}
                );
            });
    }
}