export interface AnimeData {
  images: { webp: { large_image_url: string } };
  genres: { name: string }[];
  themes: { name: string }[];
  demographics: { name: string }[];
  studios?: { name: string }[];
  authors?: { name: string }[];
  aired?: { prop: { from: { year: number } } };
  published?: { prop: { from: { year: number } } };
  episodes?: number;
  chapters?: number;
  title: string;
  score?: number;
  rank?: number;
}
