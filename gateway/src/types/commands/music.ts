export interface JamendoTrack {
  name: string;
  artist_name: string;
  album_name: string;
  duration: number;
  releasedate: string;
  image: string;
  audio: string;
}

export interface JamendoResponse {
  results: JamendoTrack[];
}

export interface DeezerTrack {
  title: string;
  artist: { name: string };
  album: { title: string; cover_medium: string };
  duration: number;
  preview: string;
}

export interface DeezerChartResponse {
  data: DeezerTrack[];
}
