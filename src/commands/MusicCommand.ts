import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import { ArgType } from '../types/commandConfig.js';
import Command from './Command.js';
import Reply from '../builders/Reply.js';
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
  readonly config: CommandConfig = {
    name: 'música',
    flags: ['free', 'show', 'dm'],
    args: ArgType.Optional,
  };
  readonly menuDescription =
    'Receba um preview de música popular (Deezer) ou use "free" para músicas completas gratuitas (Jamendo).';

  protected async execute(data: CommandData, parsed: ParsedCommand): Promise<Message[]> {
    if (parsed.flags.has('free')) {
      return this.runJamendo(data, parsed);
    }
    return this.runDeezer(data, parsed);
  }

  private async runDeezer(data: CommandData, parsed: ParsedCommand): Promise<Message[]> {
    const { tag, genreId } = this.parseDeezerGenre(parsed.rest);

    try {
      const response = await AxiosClient.get<DeezerChartResponse>(
        `https://api.deezer.com/chart/${genreId}/tracks`,
        { params: { limit: 200 } },
      );

      const tracks = response.data.data;
      if (!tracks || tracks.length === 0) {
        return [Reply.to(data).text('Não encontrei músicas para esse gênero. Tente outro! 🎵')];
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
        Reply.to(data).image(track.album.cover_medium, caption),
        Reply.to(data).audio(track.preview),
      ];
    } catch {
      return [Reply.to(data).text('Erro ao buscar música. Tente novamente mais tarde! 🎵')];
    }
  }

  private async runJamendo(data: CommandData, parsed: ParsedCommand): Promise<Message[]> {
    const genre = this.parseJamendoGenre(parsed.rest);
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
        return [Reply.to(data).text('Não encontrei músicas para esse gênero. Tente outro! 🎵')];
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

      return [Reply.to(data).image(track.image, caption), Reply.to(data).audio(track.audio)];
    } catch {
      return [Reply.to(data).text('Erro ao buscar música. Tente novamente mais tarde! 🎵')];
    }
  }

  private parseJamendoGenre(rest: string): string {
    const cleaned = rest.trim().toLowerCase();
    if (cleaned && MUSIC_GENRES.includes(cleaned)) {
      return cleaned;
    }
    return MUSIC_GENRES[Math.floor(Math.random() * MUSIC_GENRES.length)];
  }

  private parseDeezerGenre(rest: string): { tag: string; genreId: number } {
    const cleaned = rest.trim().toLowerCase();
    if (cleaned && cleaned in DEEZER_GENRES) {
      return { tag: cleaned, genreId: DEEZER_GENRES[cleaned] };
    }
    return { tag: 'all', genreId: 0 };
  }

  formatDuration(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }
}
