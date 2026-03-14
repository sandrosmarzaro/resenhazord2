export interface TCGdexCard {
  id: string;
  localId: string;
  name: string;
  category: string;
  image?: string;
  illustrator?: string;
  rarity?: string;
  hp?: number;
  types?: string[];
  stage?: string;
  set: { name: string; cardCount: { total: number; official: number } };
}
