import Command, {
  type CommandData,
  type CommandConfig,
  type ParsedCommand,
  type Message,
} from './Command.js';
import Reply from '../builders/Reply.js';
import AxiosClient from '../infra/AxiosClient.js';
import { ANIMAL_EMOJIS } from '../data/animalEmojis.js';
import { ANIMAL_WIKIPEDIA_TITLES } from '../data/animalWikipediaTitles.js';
import { Sentry } from '../infra/Sentry.js';

interface WikipediaSummaryResponse {
  extract: string;
  thumbnail?: { source: string };
}

export default class AnimalCommand extends Command {
  readonly config: CommandConfig = {
    name: 'animal',
    flags: ['show', 'dm'],
    category: 'aleatórias',
  };
  readonly menuDescription = 'Receba uma foto e curiosidade de um animal aleatório.';

  private static readonly ANIMAL_KEYS = Object.keys(ANIMAL_WIKIPEDIA_TITLES);
  private static readonly API_BASE = 'https://en.wikipedia.org/api/rest_v1/page/summary';
  private static readonly USER_AGENT = 'ResenhazordBot/2.0';
  private static readonly MAX_RETRIES = 3;

  private static formatName(type: string): string {
    return type
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }

  private static extractFact(extract: string): string {
    const sentences = extract.match(/[^.!?]*[.!?]+/g) ?? [extract];
    const fact = sentences.slice(0, 2).join('').trim();
    return fact.length > 300 ? sentences[0].trim() : fact;
  }

  private async fetchAnimal(wikiTitle: string): Promise<WikipediaSummaryResponse> {
    const response = await AxiosClient.get<WikipediaSummaryResponse>(
      `${AnimalCommand.API_BASE}/${wikiTitle}`,
      {
        retries: 0,
        timeout: 10000,
        headers: { 'User-Agent': AnimalCommand.USER_AGENT },
      },
    );
    return response.data;
  }

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
    const type =
      AnimalCommand.ANIMAL_KEYS[Math.floor(Math.random() * AnimalCommand.ANIMAL_KEYS.length)];
    const wikiTitle = ANIMAL_WIKIPEDIA_TITLES[type];
    try {
      let animalData: WikipediaSummaryResponse | undefined;
      for (let attempt = 0; attempt <= AnimalCommand.MAX_RETRIES; attempt++) {
        try {
          animalData = await this.fetchAnimal(wikiTitle);
          break;
        } catch (error) {
          const err = error as { response?: { status?: number; headers?: Record<string, string> } };
          if (err?.response?.status === 429) {
            const retryAfter = err.response.headers?.['retry-after'];
            const waitMs = retryAfter ? parseInt(retryAfter, 10) * 1000 : 60_000;
            await new Promise((resolve) => setTimeout(resolve, waitMs));
            continue;
          }
          throw error;
        }
      }
      if (!animalData) return [];
      const fact = AnimalCommand.extractFact(animalData.extract);
      const emoji = ANIMAL_EMOJIS[type];
      const name = AnimalCommand.formatName(type);
      const caption = `*${emoji} ${name}*\n\n📝 ${fact}`;
      if (!animalData.thumbnail) {
        return [Reply.to(data).text(caption)];
      }
      const buffer = await AxiosClient.getBuffer(animalData.thumbnail.source, {
        headers: { 'User-Agent': AnimalCommand.USER_AGENT },
      });
      return [Reply.to(data).imageBuffer(buffer, caption)];
    } catch (error) {
      Sentry.captureException(error, { extra: { command: 'animal' } });
      return [Reply.to(data).text('Erro ao buscar animal. Tente novamente mais tarde! 🐾')];
    }
  }
}
