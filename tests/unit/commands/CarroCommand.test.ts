import { describe, it, expect, beforeEach, vi } from 'vitest';
import CarroCommand from '../../../src/commands/CarroCommand.js';
import { GroupCommandData, PrivateCommandData } from '../../fixtures/index.js';
import AxiosClient from '../../../src/infra/AxiosClient.js';
import { Sentry } from '../../../src/infra/Sentry.js';

vi.mock('../../../src/infra/AxiosClient.js', () => ({
  default: {
    get: vi.fn(),
    getBuffer: vi.fn(),
  },
}));

const mockGet = AxiosClient.get as ReturnType<typeof vi.fn>;
const mockGetBuffer = AxiosClient.getBuffer as ReturnType<typeof vi.fn>;

const mockModels = {
  modelos: [
    { codigo: 1001, nome: 'Golf 1.6' },
    { codigo: 1002, nome: 'Polo 1.0' },
  ],
};

const mockYears = [
  { codigo: '2020-1', nome: '2020 Gasolina' },
  { codigo: '2019-1', nome: '2019 Gasolina' },
];

const mockDetails = {
  Marca: 'Volkswagen',
  Modelo: 'Golf 1.6',
  AnoModelo: 2020,
  Combustivel: 'Gasolina',
  Valor: 'R$ 80.000,00',
  CodigoFipe: '005215-9',
};

const mockWikiResponse = {
  query: {
    pages: {
      '12345': {
        thumbnail: { source: 'https://upload.wikimedia.org/thumb/a/a1/640px-Golf.jpg' },
      },
    },
  },
};

describe('CarroCommand', () => {
  let command: CarroCommand;

  beforeEach(() => {
    command = new CarroCommand();
    vi.clearAllMocks();
    mockGetBuffer.mockResolvedValue(Buffer.from('mock-image'));
    mockGet
      .mockResolvedValueOnce({ data: mockModels })
      .mockResolvedValueOnce({ data: mockYears })
      .mockResolvedValueOnce({ data: mockDetails })
      .mockResolvedValueOnce({ data: mockWikiResponse });
  });

  describe('matches()', () => {
    it.each([
      [',carro', true],
      [', carro', true],
      [', CARRO', true],
      [', carro show', true],
      [', carro dm', true],
      [', carro wiki', true],
      [', carro wiki show', true],
      [', carro show wiki', true],
      ['carro', false],
      [',carrof', false],
      ['hello', false],
    ])('"%s" → %s', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    describe('FIPE API calls', () => {
      it('should call FIPE models endpoint for the selected brand', async () => {
        vi.spyOn(Math, 'random').mockReturnValue(0);
        const data = GroupCommandData.build({ text: ',carro' });

        await command.run(data);

        expect(mockGet).toHaveBeenNthCalledWith(
          1,
          expect.stringMatching(/\/fipe\/api\/v1\/carros\/marcas\/\d+\/modelos$/),
          { retries: 0, timeout: 8000 },
        );
      });

      it('should call FIPE years endpoint with the selected model code', async () => {
        const data = GroupCommandData.build({ text: ',carro' });

        await command.run(data);

        expect(mockGet).toHaveBeenNthCalledWith(2, expect.stringMatching(/\/modelos\/\d+\/anos$/), {
          retries: 0,
          timeout: 8000,
        });
      });

      it('should call FIPE details endpoint with model code and year code', async () => {
        const data = GroupCommandData.build({ text: ',carro' });

        await command.run(data);

        expect(mockGet).toHaveBeenNthCalledWith(
          3,
          expect.stringMatching(/\/modelos\/\d+\/anos\/.+$/),
          { retries: 0, timeout: 8000 },
        );
      });
    });

    describe('Wikipedia API call', () => {
      it('should call Wikipedia search API after FIPE details', async () => {
        const data = GroupCommandData.build({ text: ',carro' });

        await command.run(data);

        expect(mockGet).toHaveBeenNthCalledWith(
          4,
          expect.stringMatching(/en\.wikipedia\.org.*api\.php.*generator=search/),
          expect.objectContaining({ retries: 0, timeout: 8000 }),
        );
      });

      it('should fetch the image buffer from the Wikipedia thumbnail URL', async () => {
        const data = GroupCommandData.build({ text: ',carro' });

        await command.run(data);

        expect(mockGetBuffer).toHaveBeenCalledWith(
          expect.stringMatching(/640px-/),
          expect.objectContaining({ timeout: 12000 }),
        );
      });

      it('should return text-only reply when Wikipedia has no thumbnail', async () => {
        mockGet.mockReset();
        mockGet
          .mockResolvedValueOnce({ data: mockModels })
          .mockResolvedValueOnce({ data: mockYears })
          .mockResolvedValueOnce({ data: mockDetails })
          .mockResolvedValueOnce({ data: { query: { pages: { '1': {} } } } }) // Wikipedia: no thumb
          .mockResolvedValueOnce({ data: {} }); // Commons: no thumb

        const data = GroupCommandData.build({ text: ',carro' });

        const messages = await command.run(data);

        expect(mockGetBuffer).not.toHaveBeenCalled();
        const content = messages[0].content as { text: string };
        expect(content.text).toContain('Volkswagen');
      });

      it('should return text-only reply when Wikipedia query is absent', async () => {
        mockGet.mockReset();
        mockGet
          .mockResolvedValueOnce({ data: mockModels })
          .mockResolvedValueOnce({ data: mockYears })
          .mockResolvedValueOnce({ data: mockDetails })
          .mockResolvedValueOnce({ data: {} }) // Wikipedia: no query
          .mockResolvedValueOnce({ data: {} }); // Commons: no thumb

        const data = GroupCommandData.build({ text: ',carro' });

        const messages = await command.run(data);

        expect(mockGetBuffer).not.toHaveBeenCalled();
        const content = messages[0].content as { text: string };
        expect(content.text).toContain('Golf');
      });

      it('should fall back to Wikimedia Commons when Wikipedia has no thumbnail', async () => {
        mockGet.mockReset();
        mockGet
          .mockResolvedValueOnce({ data: mockModels })
          .mockResolvedValueOnce({ data: mockYears })
          .mockResolvedValueOnce({ data: mockDetails })
          .mockResolvedValueOnce({ data: { query: { pages: { '1': {} } } } }) // Wikipedia: no thumb
          .mockResolvedValueOnce({
            data: {
              query: {
                pages: {
                  '99': {
                    thumbnail: {
                      source: 'https://upload.wikimedia.org/thumb/x/xx/640px-Golf.jpg',
                    },
                  },
                },
              },
            },
          }); // Commons: has thumb

        const data = GroupCommandData.build({ text: ',carro' });
        const messages = await command.run(data);

        expect(mockGetBuffer).toHaveBeenCalledWith(
          expect.stringContaining('640px-'),
          expect.objectContaining({ timeout: 12000 }),
        );
        const content = messages[0].content as { image: Buffer };
        expect(Buffer.isBuffer(content.image)).toBe(true);
      });
    });

    describe('caption', () => {
      it('should contain brand name', async () => {
        const data = GroupCommandData.build({ text: ',carro' });

        const messages = await command.run(data);

        const content = messages[0].content as { caption: string };
        expect(content.caption).toContain('Volkswagen');
      });

      it('should contain model name', async () => {
        const data = GroupCommandData.build({ text: ',carro' });

        const messages = await command.run(data);

        const content = messages[0].content as { caption: string };
        expect(content.caption).toContain('Golf 1.6');
      });

      it('should contain the year', async () => {
        const data = GroupCommandData.build({ text: ',carro' });

        const messages = await command.run(data);

        const content = messages[0].content as { caption: string };
        expect(content.caption).toContain('2020');
      });

      it('should contain the price', async () => {
        const data = GroupCommandData.build({ text: ',carro' });

        const messages = await command.run(data);

        const content = messages[0].content as { caption: string };
        expect(content.caption).toContain('R$ 80.000,00');
      });

      it('should contain the fuel type', async () => {
        const data = GroupCommandData.build({ text: ',carro' });

        const messages = await command.run(data);

        const content = messages[0].content as { caption: string };
        expect(content.caption).toContain('Gasolina');
      });
    });

    describe('year retry logic', () => {
      it('should retry the next year when FIPE returns an error object', async () => {
        mockGet.mockReset();
        mockGet
          .mockResolvedValueOnce({ data: mockModels })
          .mockResolvedValueOnce({ data: mockYears })
          .mockResolvedValueOnce({ data: { error: 'Dado não encontrado' } })
          .mockResolvedValueOnce({ data: mockDetails })
          .mockResolvedValueOnce({ data: mockWikiResponse });

        const data = GroupCommandData.build({ text: ',carro' });

        const messages = await command.run(data);

        // 5 calls: models + years + 2 detail attempts + Wikipedia
        expect(mockGet).toHaveBeenCalledTimes(5);
        const content = messages[0].content as { caption: string };
        expect(content.caption).toContain('Golf 1.6');
      });

      it('should fall back to model name caption when all year attempts fail', async () => {
        mockGet.mockReset();
        mockGet
          .mockResolvedValueOnce({ data: mockModels })
          .mockResolvedValueOnce({ data: mockYears })
          .mockResolvedValue({ data: { error: 'Dado não encontrado' } });

        const data = GroupCommandData.build({ text: ',carro' });

        const messages = await command.run(data);

        const content = messages[0].content as { text: string };
        // fallback caption still includes model name (text reply — no thumbnail)
        expect(content.text).toContain('Golf');
      });
    });

    describe('image', () => {
      it('should return an image buffer message', async () => {
        const data = GroupCommandData.build({ text: ',carro' });

        const messages = await command.run(data);

        const content = messages[0].content as { image: Buffer };
        expect(Buffer.isBuffer(content.image)).toBe(true);
      });
    });

    describe('message flags', () => {
      it('should set viewOnce to true by default', async () => {
        const data = GroupCommandData.build({ text: ',carro' });

        const messages = await command.run(data);

        const content = messages[0].content as { viewOnce: boolean };
        expect(content.viewOnce).toBe(true);
      });

      it('should set viewOnce to false with show flag', async () => {
        const data = GroupCommandData.build({ text: ',carro show' });

        const messages = await command.run(data);

        const content = messages[0].content as { viewOnce: boolean };
        expect(content.viewOnce).toBe(false);
      });

      it('should send to DM when dm flag is active in group', async () => {
        const data = GroupCommandData.build({ text: ',carro dm' });

        const messages = await command.run(data);

        expect(messages[0].jid).toBe(data.key.participant);
      });

      it('should not change jid when dm flag is active in private chat', async () => {
        const data = PrivateCommandData.build({ text: ',carro dm' });

        const messages = await command.run(data);

        expect(messages[0].jid).toBe(data.key.remoteJid);
      });

      it('should quote the original message', async () => {
        const data = GroupCommandData.build({ text: ',carro' });

        const messages = await command.run(data);

        expect(messages[0].options?.quoted).toBe(data);
      });

      it('should skip Commons fallback and return text-only when wiki flag is set and Wikipedia has no thumbnail', async () => {
        mockGet.mockReset();
        mockGet
          .mockResolvedValueOnce({ data: mockModels })
          .mockResolvedValueOnce({ data: mockYears })
          .mockResolvedValueOnce({ data: mockDetails })
          .mockResolvedValueOnce({ data: { query: { pages: { '1': {} } } } }); // Wikipedia: no thumb

        const data = GroupCommandData.build({ text: ',carro wiki' });

        const messages = await command.run(data);

        expect(mockGet).toHaveBeenCalledTimes(4);
        expect(mockGetBuffer).not.toHaveBeenCalled();
        const content = messages[0].content as { text: string };
        expect(content.text).toContain('Volkswagen');
      });
    });

    describe('error handling', () => {
      it('should return error text on API failure', async () => {
        mockGet.mockReset();
        mockGet.mockRejectedValue(new Error('Network error'));
        const data = GroupCommandData.build({ text: ',carro' });

        const messages = await command.run(data);

        expect(messages).toHaveLength(1);
        const content = messages[0].content as { text: string };
        expect(content.text).toContain('Erro ao buscar carro');
      });

      it('should call Sentry.captureException on error', async () => {
        mockGet.mockReset();
        const error = new Error('Network error');
        mockGet.mockRejectedValue(error);
        const data = GroupCommandData.build({ text: ',carro' });

        await command.run(data);

        expect(Sentry.captureException).toHaveBeenCalledWith(error, {
          extra: { command: 'carro' },
        });
      });
    });
  });
});
