import AxiosClient from '../infra/AxiosClient.js';

interface BeerResult {
  name: string;
  brand: string;
  imageUrl: string;
  alcohol?: number;
  quantity?: string;
  origin?: string;
  soldIn?: string;
  ingredients?: string;
}

interface OpenFoodFactsProduct {
  product_name?: string;
  brands?: string;
  image_front_url?: string;
  nutriments?: { alcohol_100g?: number };
  quantity?: string;
  origins?: string;
  countries?: string;
  ingredients_text?: string;
}

interface OpenFoodFactsResponse {
  products: OpenFoodFactsProduct[];
  page_count: number;
}

export default class OpenFoodFactsScraper {
  private static readonly TIMEOUT = 15000;
  private static readonly PAGE_SIZE = 20;
  private static readonly MAX_PAGE = 200;

  static async getRandomBeer(): Promise<BeerResult> {
    const page = Math.floor(Math.random() * this.MAX_PAGE) + 1;

    try {
      return await this.fetchBeerFromPage(page);
    } catch {
      const retryPage = Math.floor(Math.random() * 50) + 1;
      return this.fetchBeerFromPage(retryPage);
    }
  }

  private static async fetchBeerFromPage(page: number): Promise<BeerResult> {
    const response = await AxiosClient.get<OpenFoodFactsResponse>(
      'https://world.openfoodfacts.net/cgi/search.pl',
      {
        timeout: this.TIMEOUT,
        params: {
          action: 'process',
          tagtype_0: 'categories',
          tag_contains_0: 'contains',
          tag_0: 'beers',
          page_size: this.PAGE_SIZE,
          page,
          json: 1,
        },
      },
    );

    const products = response.data.products.filter((p) => p.product_name && p.image_front_url);

    if (products.length === 0) {
      throw new Error('Nenhuma cerveja encontrada');
    }

    const product = products[Math.floor(Math.random() * products.length)];

    return {
      name: product.product_name!,
      brand: product.brands ?? 'Desconhecida',
      imageUrl: product.image_front_url!,
      alcohol: product.nutriments?.alcohol_100g ?? undefined,
      quantity: product.quantity || undefined,
      origin: this.stripLangPrefixes(product.origins),
      soldIn: this.stripLangPrefixes(product.countries),
      ingredients: product.ingredients_text || undefined,
    };
  }

  private static stripLangPrefixes(value?: string): string | undefined {
    if (!value) return undefined;
    return value.replace(/\b[a-z]{2}:/gi, '').trim();
  }
}
