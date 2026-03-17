export interface ChampionInfo {
  attack: number;
  defense: number;
  magic: number;
  difficulty: number;
}

export interface ChampionData {
  id: string;
  name: string;
  title: string;
  tags: string[];
  info: ChampionInfo;
  blurb: string;
}

export interface ChampionListResponse {
  data: Record<string, ChampionData>;
}
