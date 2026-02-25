import type { CommandData } from '../types/command.js';
import Resenhazord2 from '../models/Resenhazord2.js';

export default class MediaCommand {
  static identifier: string = '^\\s*\\,\\s*media\\s*';

  static async run(data: CommandData): Promise<void> {
    const url = data.text.replace(/\n*\s*,\s*media\s*/, '');
    if (url.length === 0) {
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: 'Me passa o link do vídeo que você quer baixar 🤗' },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
      return;
    }
    await Resenhazord2.socket!.sendMessage(
      data.key.remoteJid!,
      { text: `Viiixxiii... Não consegui baixar o vídeo! 🥺👉👈` },
      { quoted: data, ephemeralExpiration: data.expiration },
    );
  }
}
