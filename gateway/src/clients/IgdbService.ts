import AxiosClient from '../infra/AxiosClient.js';

export interface IgdbGame {
  name: string;
  first_release_date?: number;
  genres?: { name: string }[];
  platforms?: { name: string }[];
  total_rating?: number;
  cover: { image_id: string };
}

export default class IgdbService {
  private static readonly GAMES_URL = 'https://api.igdb.com/v4/games';
  private static readonly TOKEN_URL = 'https://id.twitch.tv/oauth2/token';
  private static readonly COVER_BASE = 'https://images.igdb.com/igdb/image/upload/t_cover_big_2x';
  private static accessToken: string | null = null;

  private static async getAccessToken(): Promise<string> {
    if (IgdbService.accessToken) return IgdbService.accessToken;
    const res = await AxiosClient.post<{ access_token: string }>(IgdbService.TOKEN_URL, null, {
      params: {
        client_id: process.env.TWITCH_CLIENT_ID ?? '',
        client_secret: process.env.TWITCH_CLIENT_SECRET ?? '',
        grant_type: 'client_credentials',
      },
      retries: 0,
    });
    const token = res.data.access_token;
    IgdbService.accessToken = token;
    return token;
  }

  static coverUrl(imageId: string): string {
    return `${IgdbService.COVER_BASE}/${imageId}.jpg`;
  }

  static async getRandomGame(): Promise<IgdbGame> {
    const token = await IgdbService.getAccessToken();
    const offset = Math.floor(Math.random() * 2000);
    const body =
      `fields name,first_release_date,genres.name,platforms.name,total_rating,cover.image_id;` +
      ` where total_rating_count > 100 & cover != null;` +
      ` sort total_rating_count desc; offset ${offset}; limit 1;`;
    const res = await AxiosClient.post<IgdbGame[]>(IgdbService.GAMES_URL, body, {
      headers: {
        'Client-ID': process.env.TWITCH_CLIENT_ID ?? '',
        Authorization: `Bearer ${token}`,
        'Content-Type': 'text/plain',
      },
      retries: 0,
    });
    const game = res.data[0];
    if (!game) throw new Error('No game returned from IGDB');
    return game;
  }

  static reset(): void {
    IgdbService.accessToken = null;
  }
}
