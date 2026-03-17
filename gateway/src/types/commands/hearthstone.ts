export interface HearthstoneCard {
  name: string;
  text: string;
  flavorText: string;
  image: string;
}

export interface HearthstoneResponse {
  pageCount: number;
  cards: HearthstoneCard[];
}
