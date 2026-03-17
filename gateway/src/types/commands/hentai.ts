export interface HentaiGallery {
  title: string;
  japaneseTitle?: string;
  artists: string[];
  groups: string[];
  tags: string[];
  type: string;
  language: string;
  pages: number;
  date: string;
  coverUrl: string;
  coverHeaders?: Record<string, string>;
  url: string;
}

export interface NhentaiTag {
  id: number;
  type: string;
  name: string;
  url: string;
  count: number;
}

export interface NhentaiTitle {
  english: string;
  japanese: string;
  pretty: string;
}

export interface NhentaiImage {
  t: 'j' | 'p' | 'g' | 'w';
  w: number;
  h: number;
}

export interface NhentaiGallery {
  id: number;
  media_id: string;
  title: NhentaiTitle;
  scanlator: string;
  upload_date: number;
  tags: NhentaiTag[];
  num_pages: number;
  num_favorites: number;
  images: {
    cover: NhentaiImage;
    thumbnail: NhentaiImage;
    pages: NhentaiImage[];
  };
}
