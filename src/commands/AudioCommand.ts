import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import tts from 'google-tts-api';
import { LANGUAGES } from '../data/languages.js';

export default class AudioCommand extends Command {
  readonly regexIdentifier =
    '^\\s*\\,\\s*.udio\\s*(?:[A-Za-z]{2}\\s*\\-\\s*[A-Za-z]{2})?\\s*(?:show)?\\s*(?:dm)?';
  readonly menuDescription =
    'Converta texto em audio usando a voz do Google, podendo trocar a língua.';

  async run(data: CommandData): Promise<Message[]> {
    let chat_id: string = data.key.remoteJid!;
    const DM_FLAG_ACTIVE = data.text.match(/dm/);
    if (DM_FLAG_ACTIVE && data.key.participant) {
      chat_id = data.key.participant;
    }

    const rest_command = data.text.replace(/\n*\s*,\s*.udio\s*/, '');
    const is_language_inserted = rest_command.match(/^[A-Za-z]{2}\s*-\s*[A-Za-z]{2}/);
    const language = is_language_inserted ? is_language_inserted[0] : 'pt-br';
    if (!LANGUAGES.includes(language.toLowerCase())) {
      return [
        {
          jid: chat_id,
          content: { text: 'Burro burro! O idioma 🏳️‍🌈 não existe!' },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }
    let text;
    if (is_language_inserted) {
      text = rest_command.replace(is_language_inserted[0], '');
    } else {
      text = rest_command;
    }
    if (!text) {
      return [
        {
          jid: chat_id,
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
          jid: chat_id,
          content: {
            viewOnce: !data.text.match(/show/),
            audio: { url: audio_urls[0].url },
          },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }

    return audio_urls.map((audio_url: { url: string }) => ({
      jid: chat_id,
      content: {
        viewOnce: !data.text.match(/show/),
        audio: { url: audio_url.url },
      },
      options: { quoted: data, ephemeralExpiration: data.expiration },
    }));
  }
}
