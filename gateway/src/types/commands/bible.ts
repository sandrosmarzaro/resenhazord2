export interface VerseData {
  book: { name: string };
  chapter: number;
  number: number;
  text: string;
}

export interface BookData {
  name: string;
  abbrev?: { pt: string };
}
