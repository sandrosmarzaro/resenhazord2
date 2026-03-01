import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import AxiosClient from '../infra/AxiosClient.js';
import { MUSIC_GENRES } from '../data/musicGenres.js';
import { DEEZER_GENRES } from '../data/deezerGenres.js';

interface JamendoTrack {
  name: string;
  artist_name: string;
  album_name: string;
  duration: number;
  releasedate: string;
  image: string;
  audio: string;
}

interface JamendoResponse {
  results: JamendoTrack[];
}

interface DeezerTrack {
  title: string;
  artist: { name: string };
  album: { title: string; cover_medium: string };
  duration: number;
  preview: string;
}

interface DeezerChartResponse {
  data: DeezerTrack[];
}

export default class MusicCommand extends Command {
  readonly regexIdentifier =
    '^\\s*\\,\\s*m.sica\\s*(?:free)?\\s*(?:[a-z]+)?\\s*(?:show)?\\s*(?:dm)?$';
  readonly menuDescription =
    'Receba um preview de música popular (Deezer) ou use "free" para músicas completas gratuitas (Jamendo).';

  async run(data: CommandData): Promise<Message[]> {
    const isFree = /free/i.test(data.text);
    if (isFree) {
      return this.runJamendo(data);
    }
    return this.runDeezer(data);
  }

  private async runDeezer(data: CommandData): Promise<Message[]> {
    let chat_id: string = data.key.remoteJid!;
    const DM_FLAG_ACTIVE = data.text.match(/dm/);
    if (DM_FLAG_ACTIVE && data.key.participant) {
      chat_id = data.key.participant;
    }

    const { tag, genreId } = this.parseDeezerGenre(data.text);

    try {
      const response = await AxiosClient.get<DeezerChartResponse>(
        `https://api.deezer.com/chart/${genreId}/tracks`,
        { params: { limit: 200 } },
      );

      const tracks = response.data.data;
      if (!tracks || tracks.length === 0) {
        return [
          {
            jid: chat_id,
            content: { text: 'Não encontrei músicas para esse gênero. Tente outro! 🎵' },
            options: { quoted: data, ephemeralExpiration: data.expiration },
          },
        ];
      }

      const track = tracks[Math.floor(Math.random() * tracks.length)];
      const duration = this.formatDuration(track.duration);
      const caption =
        `🎵 *${track.title}*\n` +
        `👨‍🦱 _${track.artist.name}_\n` +
        `> 📚 ${track.album.title}\n` +
        `> 🧬 ${tag}\n` +
        `> ⏱️ ${duration}`;

      return [
        {
          jid: chat_id,
          content: {
            viewOnce: !data.text.match(/show/),
            caption,
            image: { url: track.album.cover_medium },
          },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
        {
          jid: chat_id,
          content: {
            viewOnce: !data.text.match(/show/),
            mimetype: 'audio/mp4',
            audio: { url: track.preview },
          },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    } catch {
      return [
        {
          jid: chat_id,
          content: { text: 'Erro ao buscar música. Tente novamente mais tarde! 🎵' },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }
  }

  private async runJamendo(data: CommandData): Promise<Message[]> {
    let chat_id: string = data.key.remoteJid!;
    const DM_FLAG_ACTIVE = data.text.match(/dm/);
    if (DM_FLAG_ACTIVE && data.key.participant) {
      chat_id = data.key.participant;
    }

    const genre = this.parseJamendoGenre(data.text);
    const clientId = process.env.JAMENDO_CLIENT_ID;

    try {
      const response = await AxiosClient.get<JamendoResponse>(
        'https://api.jamendo.com/v3.0/tracks/',
        {
          params: {
            client_id: clientId!,
            format: 'json',
            limit: 200,
            tags: genre,
            order: 'popularity_total',
            imagesize: 500,
            audioformat: 'mp32',
          },
        },
      );

      const tracks = response.data.results;
      if (!tracks || tracks.length === 0) {
        return [
          {
            jid: chat_id,
            content: { text: 'Não encontrei músicas para esse gênero. Tente outro! 🎵' },
            options: { quoted: data, ephemeralExpiration: data.expiration },
          },
        ];
      }

      const track = tracks[Math.floor(Math.random() * tracks.length)];
      const duration = this.formatDuration(track.duration);
      const caption =
        `🎵 *${track.name}*\n` +
        `👨‍🦱 _${track.artist_name}_\n` +
        `> 📚 ${track.album_name}\n` +
        `> 🧬 ${genre}\n` +
        `> ⏱️ ${duration}\n` +
        `> 📅 ${track.releasedate}`;

      return [
        {
          jid: chat_id,
          content: {
            viewOnce: !data.text.match(/show/),
            caption,
            image: { url: track.image },
          },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
        {
          jid: chat_id,
          content: {
            viewOnce: !data.text.match(/show/),
            mimetype: 'audio/mp4',
            audio: { url: track.audio },
          },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    } catch {
      return [
        {
          jid: chat_id,
          content: { text: 'Erro ao buscar música. Tente novamente mais tarde! 🎵' },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }
  }

  private parseJamendoGenre(text: string): string {
    const cleaned = text
      .replace(/^\s*,\s*m.sica\s*/i, '')
      .replace(/\s*free\s*/gi, '')
      .replace(/\s*show\s*/gi, '')
      .replace(/\s*dm\s*/gi, '')
      .trim();

    if (cleaned && MUSIC_GENRES.includes(cleaned.toLowerCase())) {
      return cleaned.toLowerCase();
    }

    return MUSIC_GENRES[Math.floor(Math.random() * MUSIC_GENRES.length)];
  }

  private parseDeezerGenre(text: string): { tag: string; genreId: number } {
    const cleaned = text
      .replace(/^\s*,\s*m.sica\s*/i, '')
      .replace(/\s*show\s*/gi, '')
      .replace(/\s*dm\s*/gi, '')
      .trim();

    if (cleaned && cleaned.toLowerCase() in DEEZER_GENRES) {
      return { tag: cleaned.toLowerCase(), genreId: DEEZER_GENRES[cleaned.toLowerCase()] };
    }

    return { tag: 'all', genreId: 0 };
  }

  formatDuration(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }
}
