import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import { ArgType } from '../types/commandConfig.js';
import Command from './Command.js';
import Reply from '../builders/Reply.js';
import tts from 'google-tts-api';
import { LANGUAGES } from '../data/languages.js';

export default class AudioCommand extends Command {
  readonly config: CommandConfig = {
    name: 'áudio',
    options: [{ name: 'lang', pattern: '[A-Za-z]{2}-[A-Za-z]{2}' }],
    flags: ['show', 'dm'],
    args: ArgType.Optional,
  };
  readonly menuDescription =
    'Converta texto em audio usando a voz do Google, podendo trocar a língua.';

  protected async execute(data: CommandData, parsed: ParsedCommand): Promise<Message[]> {
    const language = parsed.options.get('lang') || 'pt-br';
    if (!LANGUAGES.includes(language.toLowerCase())) {
      return [Reply.to(data).text('Burro burro! O idioma 🏳️‍🌈 não existe!')];
    }

    const text = parsed.rest.trim();
    if (!text) {
      return [Reply.to(data).text('Burro burro! Cadê o texto? 🤨')];
    }

    const audio_urls = tts.getAllAudioUrls(text, {
      lang: language,
      slow: false,
      host: 'https://translate.google.com',
      splitPunct: '.!?;:',
    });

    const char_limit = 200;
    if (!(text.length > char_limit)) {
      return [Reply.to(data).audio(audio_urls[0].url)];
    }

    return audio_urls.map((audio_url: { url: string }) => Reply.to(data).audio(audio_url.url));
  }
}
