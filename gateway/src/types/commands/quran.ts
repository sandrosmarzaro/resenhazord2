export interface AyahData {
  text: string;
  numberInSurah: number;
  surah: {
    number: number;
    name: string;
    englishName: string;
    numberOfAyahs: number;
  };
}
