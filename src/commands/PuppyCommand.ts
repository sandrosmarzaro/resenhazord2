import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import Reply from '../builders/Reply.js';
import AxiosClient from '../infra/AxiosClient.js';
import { Sentry } from '../infra/Sentry.js';

interface DogCeoResponse {
  message: string;
  status: string;
}

interface CataasResponse {
  id: string;
  url: string;
  tags: string[];
}

export default class PuppyCommand extends Command {
  readonly config: CommandConfig = {
    name: 'puppy',
    flags: ['show', 'dm'],
    options: [{ name: 'tipo', values: ['dog', 'cat'] }],
    category: 'aleatórias',
  };
  readonly menuDescription = 'Receba uma foto aleatória de cachorro ou gato.';

  private static extractBreed(imageUrl: string): string {
    const match = imageUrl.match(/breeds\/([^/]+)\//);
    if (!match) return 'Dog';
    return match[1]
      .split('-')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }

  private async fetchDog(data: CommandData): Promise<Message[]> {
    const response = await AxiosClient.get<DogCeoResponse>(
      'https://dog.ceo/api/breeds/image/random',
      { retries: 0, timeout: 10000 },
    );
    const imageUrl = response.data.message;
    const breed = PuppyCommand.extractBreed(imageUrl);
    const buffer = await AxiosClient.getBuffer(imageUrl);
    return [Reply.to(data).imageBuffer(buffer, `🐶 ${breed}`)];
  }

  private async fetchCat(data: CommandData): Promise<Message[]> {
    const response = await AxiosClient.get<CataasResponse>('https://cataas.com/cat?json=true', {
      retries: 0,
      timeout: 10000,
    });
    const imageUrl = response.data.url;
    const buffer = await AxiosClient.getBuffer(imageUrl, { headers: { Accept: '*/*' } });
    return [Reply.to(data).imageBuffer(buffer, '🐱 Cat')];
  }

  protected async execute(data: CommandData, parsed: ParsedCommand): Promise<Message[]> {
    try {
      const tipo = parsed.options.get('tipo') ?? (Math.random() < 0.5 ? 'dog' : 'cat');
      if (tipo === 'dog') {
        return await this.fetchDog(data);
      }
      return await this.fetchCat(data);
    } catch (error) {
      Sentry.captureException(error, { extra: { command: 'puppy' } });
      return [Reply.to(data).text('Erro ao buscar imagem. Tente novamente mais tarde! 🐾')];
    }
  }
}
