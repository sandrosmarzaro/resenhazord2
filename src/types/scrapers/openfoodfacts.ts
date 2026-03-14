export interface BeerResult {
  name: string;
  brand: string;
  imageUrl: string;
  alcohol?: number;
  quantity?: string;
  origin?: string;
  soldIn?: string;
  ingredients?: string;
}

export interface OpenFoodFactsProduct {
  product_name?: string;
  brands?: string;
  image_front_url?: string;
  nutriments?: { alcohol_100g?: number };
  quantity?: string;
  origins?: string;
  countries?: string;
  ingredients_text?: string;
}

export interface OpenFoodFactsResponse {
  products: OpenFoodFactsProduct[];
  page_count: number;
}
