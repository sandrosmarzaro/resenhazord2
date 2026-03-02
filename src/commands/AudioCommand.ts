import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import { ArgType } from '../types/commandConfig.js';
import Command from './Command.js';
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
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: 'Burro burro! O idioma 🏳️‍🌈 não existe!' },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }

    const text = parsed.rest.trim();
    if (!text) {
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: 'Burro burro! Cadê o texto? 🤨' },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }

    const audio_urls = tts.getAllAudioUrls(text, {
      lang: language,
      slow: false,
      host: 'https://translate.google.com',
      splitPunct: '.!?;:',
    });

    const char_limit = 200;
    if (!(text.length > char_limit)) {
      return [
        {
          jid: data.key.remoteJid!,
          content: {
            viewOnce: true,
            mimetype: 'audio/mp4',
            audio: { url: audio_urls[0].url },
          },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }

    return audio_urls.map((audio_url: { url: string }) => ({
      jid: data.key.remoteJid!,
      content: {
        viewOnce: true,
        mimetype: 'audio/mp4',
        audio: { url: audio_url.url },
      },
      options: { quoted: data, ephemeralExpiration: data.expiration },
    }));
  }
}
