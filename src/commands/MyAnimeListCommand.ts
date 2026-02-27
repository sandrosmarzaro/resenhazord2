import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import axios from 'axios';

export default class MyAnimeListCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*(?:anime|manga)\\s*(?:show)?\\s*(?:dm)?$';
  readonly menuDescription = 'Receba um anime ou mangá aleatório do top 500 do MyAnimeList.';

  async run(data: CommandData): Promise<Message[]> {
    const base_url = 'https://api.jikan.moe/v4';
    const type = data.text.match(/anime/) ? 'anime' : 'manga';
    const page = Math.floor(Math.random() * 20) + 1;

    const response = await axios.get(base_url + `/top/${type}`, { params: { page: page } });
    const animes = response.data.data;
    const anime = animes[Math.floor(Math.random() * animes.length)];

    const image = anime.images.webp.large_image_url;
    const genres = anime.genres.map((genre: { name: string }) => genre.name).join(', ');
    const themes = anime.themes.map((theme: { name: string }) => theme.name).join(', ');
    const demos = anime.demographics
      .map((demographic: { name: string }) => demographic.name)
      .join(', ');
    let creator_emoji;
    let creators;
    let release_date;
    let size;
    let size_emoji;
    if (data.text.match(/anime/)) {
      creator_emoji = '🎙️';
      creators = anime.studios.map((studio: { name: string }) => studio.name).join(', ');
      release_date = anime.aired.prop.from.year;
      size = anime.episodes;
      size_emoji = '🎥';
    } else {
      creator_emoji = '🖋';
      creators = anime.authors.map((author: { name: string }) => author.name).join(', ');
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

    let chat_id: string = data.key.remoteJid!;
    const DM_FLAG_ACTIVE = data.text.match(/dm/);
    if (DM_FLAG_ACTIVE && data.key.participant) {
      chat_id = data.key.participant;
    }
    return [
      {
        jid: chat_id,
        content: { image: { url: image }, caption: caption, viewOnce: !data.text.match(/show/) },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }
}
