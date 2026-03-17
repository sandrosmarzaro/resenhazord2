export interface PokemonResponse {
  name: string;
  id: number;
  types: { type: { name: string } }[];
  sprites: {
    front_default: string;
    other: { 'official-artwork': { front_default: string | null } };
  };
}
