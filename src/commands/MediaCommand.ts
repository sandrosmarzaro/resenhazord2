import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';

export default class MediaCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*media\\s*';
  readonly menuDescription = 'Baixe o vídeo do link especificado de várias redes sociais.';

  async run(data: CommandData): Promise<Message[]> {
    const url = data.text.replace(/\n*\s*,\s*media\s*/, '');
    if (url.length === 0) {
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: 'Me passa o link do vídeo que você quer baixar 🤗' },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }
    return [
      {
        jid: data.key.remoteJid!,
        content: { text: `Viiixxiii... Não consegui baixar o vídeo! 🥺👉👈` },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }
}
