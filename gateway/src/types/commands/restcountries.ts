export interface RestCountry {
  name: { common: string; official: string };
  flags: { png: string };
  flag: string;
  capital?: string[];
  region: string;
  subregion?: string;
  population: number;
  area: number;
  languages?: Record<string, string>;
  currencies?: Record<string, { name: string; symbol: string }>;
}
