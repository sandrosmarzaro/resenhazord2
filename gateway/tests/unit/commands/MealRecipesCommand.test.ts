import { describe, it, expect, beforeEach, vi } from 'vitest';
import MealRecipesCommand from '../../../src/commands/MealRecipesCommand.js';
import { GroupCommandData, PrivateCommandData } from '../../fixtures/index.js';
import AxiosClient from '../../../src/infra/AxiosClient.js';

vi.mock('../../../src/infra/AxiosClient.js', () => ({
  default: {
    get: vi.fn(),
  },
}));

const mockGet = AxiosClient.get as ReturnType<typeof vi.fn>;

const mockMeal: Record<string, string> = {
  strMeal: 'Chicken Tikka Masala',
  strArea: 'Indian',
  strCategory: 'Chicken',
  strTags: 'Curry,Spicy',
  strMealThumb: 'https://www.themealdb.com/images/media/meals/chicken.jpg',
  strInstructions: 'Cook the chicken with spices.',
  strYoutube: 'https://youtube.com/watch?v=123',
  strSource: 'https://example.com/recipe',
  strIngredient1: 'Chicken',
  strMeasure1: '500g',
  strIngredient2: 'Tikka paste',
  strMeasure2: '2 tbsp',
  strIngredient3: '',
  strMeasure3: '',
};

describe('MealRecipesCommand', () => {
  let command: MealRecipesCommand;

  beforeEach(() => {
    command = new MealRecipesCommand();
    vi.clearAllMocks();
  });

  describe('matches()', () => {
    it.each([
      [', comida', true],
      [',comida', true],
      [', COMIDA', true],
      ['  , comida  ', true],
      ['comida', false],
      ['hello', false],
      [', comida extra', false],
      [',comida show', true],
      [',comida dm', true],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return meal with ingredients and caption', async () => {
      mockGet.mockResolvedValue({ data: { meals: [mockMeal] } });
      const data = GroupCommandData.build({ text: ',comida' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { caption: string; image: { url: string } };
      expect(content.image.url).toBe(mockMeal.strMealThumb);
      expect(content.caption).toContain('*Chicken Tikka Masala*');
      expect(content.caption).toContain('Indian');
      expect(content.caption).toContain('Ingredientes');
      expect(content.caption).toContain('Chicken | 500g');
      expect(content.caption).toContain('Tikka paste | 2 tbsp');
      expect(content.caption).toContain('Passo a passo');
      expect(content.caption).toContain('Cook the chicken with spices.');
    });

    it('should call themealdb API', async () => {
      mockGet.mockResolvedValue({ data: { meals: [mockMeal] } });
      const data = GroupCommandData.build({ text: ',comida' });

      await command.run(data);

      expect(mockGet).toHaveBeenCalledWith('https://www.themealdb.com/api/json/v1/1/random.php');
    });

    it('should quote the original message', async () => {
      mockGet.mockResolvedValue({ data: { meals: [mockMeal] } });
      const data = GroupCommandData.build({ text: ',comida' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      mockGet.mockResolvedValue({ data: { meals: [mockMeal] } });
      const data = GroupCommandData.build({ text: ',comida', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });

    it('should set viewOnce to true by default', async () => {
      mockGet.mockResolvedValue({ data: { meals: [mockMeal] } });
      const data = GroupCommandData.build({ text: ',comida' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(true);
    });

    it('should set viewOnce to false with show flag', async () => {
      mockGet.mockResolvedValue({ data: { meals: [mockMeal] } });
      const data = GroupCommandData.build({ text: ',comida show' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(false);
    });

    it('should send to DM when dm flag is active in group', async () => {
      mockGet.mockResolvedValue({ data: { meals: [mockMeal] } });
      const data = GroupCommandData.build({ text: ',comida dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.participant);
    });

    it('should not change jid when dm flag is active in private chat', async () => {
      mockGet.mockResolvedValue({ data: { meals: [mockMeal] } });
      const data = PrivateCommandData.build({ text: ',comida dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.remoteJid);
    });
  });
});
