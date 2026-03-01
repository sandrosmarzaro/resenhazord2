import AxiosClient from '../infra/AxiosClient.js';

interface ChampionInfo {
  attack: number;
  defense: number;
  magic: number;
  difficulty: number;
}

interface ChampionData {
  id: string;
  name: string;
  title: string;
  tags: string[];
  info: ChampionInfo;
  blurb: string;
}

interface ChampionListResponse {
  data: Record<string, ChampionData>;
}

export interface ChampionResult {
  id: string;
  name: string;
  title: string;
  tags: string[];
  info: ChampionInfo;
  blurb: string;
  splashUrl: string;
}

export default class DataDragonService {
  private static readonly TIMEOUT = 15000;

  static async getRandomChampion(): Promise<ChampionResult> {
    const version = await this.getLatestVersion();
    const champions = await this.getAllChampions(version);

    const keys = Object.keys(champions);
    const champion = champions[keys[Math.floor(Math.random() * keys.length)]];

    return {
      id: champion.id,
      name: champion.name,
      title: champion.title,
      tags: champion.tags,
      info: champion.info,
      blurb: champion.blurb,
      splashUrl: `https://ddragon.leagueoflegends.com/cdn/img/champion/splash/${champion.id}_0.jpg`,
    };
  }

  private static async getLatestVersion(): Promise<string> {
    const response = await AxiosClient.get<string[]>(
      'https://ddragon.leagueoflegends.com/api/versions.json',
      { timeout: this.TIMEOUT },
    );
    return response.data[0];
  }

  private static async getAllChampions(version: string): Promise<Record<string, ChampionData>> {
    const response = await AxiosClient.get<ChampionListResponse>(
      `https://ddragon.leagueoflegends.com/cdn/${version}/data/pt_BR/champion.json`,
      { timeout: this.TIMEOUT },
    );
    return response.data.data;
  }
}
