import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import axios from 'axios';
import Command from './Command.js';
import Reply from '../builders/Reply.js';
import AxiosClient from '../infra/AxiosClient.js';
import { ANIMAL_EMOJIS } from '../data/animalEmojis.js';
import { Sentry } from '../infra/Sentry.js';

interface AnimalResponse {
  image: string;
  fact: string;
}

export default class AnimalCommand extends Command {
  readonly config: CommandConfig = {
    name: 'animal',
    flags: ['show', 'dm'],
    category: 'aleatórias',
  };
  readonly menuDescription = 'Receba uma foto e curiosidade de um animal aleatório.';

  private static readonly ANIMAL_TYPES = [
    'dog',
    'cat',
    'bird',
    'fox',
    'kangaroo',
    'koala',
    'panda',
    'raccoon',
    'red_panda',
    'dolphin',
  ];

  private static formatName(type: string): string {
    return type
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
    try {
      const type =
        AnimalCommand.ANIMAL_TYPES[Math.floor(Math.random() * AnimalCommand.ANIMAL_TYPES.length)];
      const response = await AxiosClient.get<AnimalResponse>(
        `https://some-random-api.com/animal/${type}`,
        { retries: 0, timeout: 10000 },
      );
      const { image, fact } = response.data;
      const emoji = ANIMAL_EMOJIS[type];
      const name = AnimalCommand.formatName(type);
      const caption = `*${emoji} ${name}*\n\n📝 ${fact}`;
      const buffer = await AxiosClient.getBuffer(image);
      return [Reply.to(data).imageBuffer(buffer, caption)];
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 429) {
        return [
          Reply.to(data).text('Muitas requisições no momento. Tente novamente em 1 minuto! 🐾'),
        ];
      }
      Sentry.captureException(error, { extra: { command: 'animal' } });
      return [Reply.to(data).text('Erro ao buscar animal. Tente novamente mais tarde! 🐾')];
    }
  }
}
