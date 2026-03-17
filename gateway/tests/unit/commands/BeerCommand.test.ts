import { describe, it, expect, beforeEach, vi } from 'vitest';
import BeerCommand from '../../../src/commands/BeerCommand.js';
import { GroupCommandData, PrivateCommandData } from '../../fixtures/index.js';
import AxiosClient from '../../../src/infra/AxiosClient.js';

const mockBeerProduct = {
  product_name: 'Paulaner Weissbier',
  brands: 'Paulaner München',
  image_front_url: 'https://images.openfoodfacts.org/images/products/beer.jpg',
  nutriments: { alcohol_100g: 5.5 },
  quantity: '500 ml',
  origins: 'Alemanha',
  countries: 'Brasil, Alemanha',
  ingredients_text: 'water, wheat malt, barley malt, hops, yeast',
};

const mockApiResponse = {
  products: [
    mockBeerProduct,
    { product_name: 'No Image Beer', brands: 'Unknown' },
    {
      product_name: 'Another Beer',
      brands: 'Brewdog',
      image_front_url: 'https://images.openfoodfacts.org/images/products/another.jpg',
      nutriments: { alcohol_100g: 5.5 },
      quantity: '500 ml',
      origins: 'Alemanha',
      countries: 'Brasil, Alemanha',
      ingredients_text: 'water, wheat malt, barley malt, hops, yeast',
    },
  ],
  page_count: 228,
};

vi.mock('../../../src/infra/AxiosClient.js', () => ({
  default: {
    get: vi.fn(),
  },
}));

const mockGet = AxiosClient.get as ReturnType<typeof vi.fn>;

describe('BeerCommand', () => {
  let command: BeerCommand;

  beforeEach(() => {
    command = new BeerCommand();
    vi.clearAllMocks();
  });

  describe('matches()', () => {
    it.each([
      [',cerveja', true],
      [', cerveja', true],
      [',cerveja show', true],
      [',cerveja dm', true],
      [',cerveja show dm', true],
      ['  ,  cerveja  ', true],
      ['cerveja', false],
      [',cerveja foo', false],
      ['hello', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return 1 message with image and caption on success', async () => {
      mockGet.mockResolvedValue({ data: mockApiResponse });
      const data = GroupCommandData.build({ text: ',cerveja' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as {
        viewOnce: boolean;
        caption: string;
        image: { url: string };
      };
      expect(content.image.url).toMatch(/^https:\/\/images\.openfoodfacts\.org/);
      expect(content.caption).toContain('🍺');
      expect(content.caption).toContain('🏭');
      expect(content.caption).toContain('🍷 5.5% · 500 ml');
      expect(content.caption).toContain('📍 _Alemanha_');
      expect(content.caption).toContain('🌍 _Brasil, Alemanha_');
      expect(content.caption).toContain('> water, wheat malt, barley malt, hops, yeast');
    });

    it('should call Open Food Facts API with correct parameters', async () => {
      mockGet.mockResolvedValue({ data: mockApiResponse });
      const data = GroupCommandData.build({ text: ',cerveja' });

      await command.run(data);

      expect(AxiosClient.get).toHaveBeenCalledWith(
        'https://world.openfoodfacts.net/cgi/search.pl',
        expect.objectContaining({
          params: expect.objectContaining({
            action: 'process',
            tag_0: 'beers',
            json: 1,
          }),
        }),
      );
    });

    it('should set viewOnce to true by default', async () => {
      mockGet.mockResolvedValue({ data: mockApiResponse });
      const data = GroupCommandData.build({ text: ',cerveja' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(true);
    });

    it('should set viewOnce to false with show flag', async () => {
      mockGet.mockResolvedValue({ data: mockApiResponse });
      const data = GroupCommandData.build({ text: ',cerveja show' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(false);
    });

    it('should send to DM when dm flag is active in group', async () => {
      mockGet.mockResolvedValue({ data: mockApiResponse });
      const data = GroupCommandData.build({ text: ',cerveja dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.participant);
    });

    it('should not change jid when dm flag is active in private chat', async () => {
      mockGet.mockResolvedValue({ data: mockApiResponse });
      const data = PrivateCommandData.build({ text: ',cerveja dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.remoteJid);
    });

    it('should retry with a lower page on first API failure', async () => {
      mockGet
        .mockRejectedValueOnce(new Error('API Error'))
        .mockResolvedValueOnce({ data: mockApiResponse });
      const data = GroupCommandData.build({ text: ',cerveja' });

      const messages = await command.run(data);

      expect(mockGet).toHaveBeenCalledTimes(2);
      expect(messages).toHaveLength(1);
      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('🍺');
    });

    it('should return error message when both attempts fail', async () => {
      mockGet.mockRejectedValue(new Error('API Error'));
      const data = GroupCommandData.build({ text: ',cerveja' });

      const messages = await command.run(data);

      expect(mockGet).toHaveBeenCalledTimes(2);
      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Erro ao buscar cerveja');
    });

    it('should return error message when no beers with images are found on both attempts', async () => {
      mockGet.mockResolvedValue({
        data: { products: [{ product_name: 'No Image', brands: 'X' }], page_count: 1 },
      });
      const data = GroupCommandData.build({ text: ',cerveja' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Erro ao buscar cerveja');
    });

    it('should include ephemeral expiration from data', async () => {
      mockGet.mockResolvedValue({ data: mockApiResponse });
      const data = GroupCommandData.build({ text: ',cerveja', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });

    it('should quote the original message', async () => {
      mockGet.mockResolvedValue({ data: mockApiResponse });
      const data = GroupCommandData.build({ text: ',cerveja' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should strip language prefixes from country and origin fields', async () => {
      mockGet.mockResolvedValue({
        data: {
          products: [
            {
              product_name: 'Timișoreana',
              brands: 'Timișoreana',
              image_front_url: 'https://images.openfoodfacts.org/images/products/timi.jpg',
              nutriments: { alcohol_100g: 5 },
              origins: 'en:romania',
              countries: 'en:germany,en:romania',
            },
          ],
          page_count: 1,
        },
      });
      const data = GroupCommandData.build({ text: ',cerveja' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('📍 _romania_');
      expect(content.caption).toContain('🌍 _germany,romania_');
      expect(content.caption).not.toContain('en:');
    });
  });
});
