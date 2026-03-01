import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import AxiosClient from '../infra/AxiosClient.js';
import { MUSIC_GENRES } from '../data/musicGenres.js';

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

export default class MusicCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*m.sica\\s*(?:[a-z]+)?\\s*(?:show)?\\s*(?:dm)?$';
  readonly menuDescription = 'Receba uma música aleatória de um gênero à sua escolha.';

  async run(data: CommandData): Promise<Message[]> {
    let chat_id: string = data.key.remoteJid!;
    const DM_FLAG_ACTIVE = data.text.match(/dm/);
    if (DM_FLAG_ACTIVE && data.key.participant) {
      chat_id = data.key.participant;
    }

    const genre = this.parseGenre(data.text);
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

  private parseGenre(text: string): string {
    const cleaned = text
      .replace(/^\s*,\s*m.sica\s*/i, '')
      .replace(/\s*show\s*/gi, '')
      .replace(/\s*dm\s*/gi, '')
      .trim();

    if (cleaned && MUSIC_GENRES.includes(cleaned.toLowerCase())) {
      return cleaned.toLowerCase();
    }

    return MUSIC_GENRES[Math.floor(Math.random() * MUSIC_GENRES.length)];
  }

  formatDuration(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }
}
