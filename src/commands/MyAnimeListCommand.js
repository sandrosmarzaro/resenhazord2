import Resenhazord2 from '../models/Resenhazord2.js';
import axios from 'axios';

export default class MyAnimeListCommand {
  static identifier = '^\\s*\\,\\s*(?:anime|manga)\\s*(?:show)?\\s*(?:dm)?$';

  static async run(data) {
    const base_url = 'https://api.jikan.moe/v4';
    const type = data.text.match(/anime/) ? 'anime' : 'manga';
    const page = Math.floor(Math.random() * 20) + 1;

    await axios
      .get(base_url + `/top/${type}`, { params: { page: page } })
      .then(async (response) => {
        const animes = response.data.data;
        const anime = animes[Math.floor(Math.random() * animes.length)];

        const image = anime.images.webp.large_image_url;
        const genres = anime.genres.map((genre) => genre.name).join(', ');
        const themes = anime.themes.map((theme) => theme.name).join(', ');
        const demos = anime.demographics.map((demographic) => demographic.name).join(', ');
        let creator_emoji;
        let creators;
        let release_date;
        let size;
        let size_emoji;
        if (data.text.match(/anime/)) {
          creator_emoji = '🎙️';
          creators = anime.studios.map((studio) => studio.name).join(', ');
          release_date = anime.aired.prop.from.year;
          size = anime.episodes;
          size_emoji = '🎥';
        } else {
          creator_emoji = '🖋';
          creators = anime.authors.map((author) => author.name).join(', ');
          release_date = anime.published.prop.from.year;
          size = anime.chapters;
          size_emoji = '📚';
        }

        let caption = '';
        caption += `*${anime.title}*\n\n`;
        caption += `${size_emoji} ${size || '?'}x \t📅 ${release_date || '?'}\n`;
        caption += `⭐️ ${anime.score || '?'} \t🏆 #${anime.rank || '?'}\n`;
        caption += `🧬 ${genres || 'Desconhecido'}\n`;
        caption += `📜 ${themes || 'Desconhecido'}\n`;
        caption += `📈 ${demos || 'Desconhecido'}\n`;
        caption += `${creator_emoji} ${creators || 'Desconhecido'}`;

        let chat_id = data.key.remoteJid;
        const DM_FLAG_ACTIVE = data.text.match(/dm/);
        if (DM_FLAG_ACTIVE && data.key.participant) {
          chat_id = data.key.participant;
        }
        await Resenhazord2.socket.sendMessage(
          chat_id,
          { image: { url: image }, caption: caption, viewOnce: !data.text.match(/show/) },
          { quoted: data, ephemeralExpiration: data.expiration },
        );
      })
      .catch(async (error) => {
        console.log(`MYANIMELIST COMMAND ERROR\n${error}`);
        await Resenhazord2.socket.sendMessage(
          data.key.remoteJid,
          { text: `Viiixxiii... Não consegui encontrar seu anime! 🥺👉👈` },
          { quoted: data, ephemeralExpiration: data.expiration },
        );
      });
  }
}
