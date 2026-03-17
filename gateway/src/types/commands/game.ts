export interface GameInfo {
  name: string;
  year: string;
  genres: string;
  platforms: string;
  rating: string | null;
  coverUrl: string;
}

export interface GameSource {
  fetch(): Promise<GameInfo>;
}

export interface RawgPlatform {
  platform: { name: string };
}

export interface RawgGenre {
  name: string;
}

export interface RawgGame {
  name: string;
  released?: string;
  background_image?: string;
  metacritic?: number;
  genres: RawgGenre[];
  platforms?: RawgPlatform[];
}

export interface RawgResponse {
  results: RawgGame[];
}
