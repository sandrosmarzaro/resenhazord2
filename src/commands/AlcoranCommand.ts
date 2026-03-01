import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import AxiosClient from '../infra/AxiosClient.js';

interface AyahData {
  text: string;
  numberInSurah: number;
  surah: {
    number: number;
    name: string;
    englishName: string;
    numberOfAyahs: number;
  };
}

export default class AlcoranCommand extends Command {
  readonly regexIdentifier = '^\\s*,\\s*alcor[aã]o\\s*$';
  readonly menuDescription = 'Receba um versículo aleatório do Alcorão em português.';

  private static readonly TOTAL_AYAHS = 6236;

  async run(data: CommandData): Promise<Message[]> {
    const ayahNumber = Math.floor(Math.random() * AlcoranCommand.TOTAL_AYAHS) + 1;
    const url = `https://api.alquran.cloud/v1/ayah/${ayahNumber}/pt.elhayek`;
    const response = await AxiosClient.get<{ data: AyahData }>(url);
    const ayah = response.data.data;

    return [
      {
        jid: data.key.remoteJid!,
        content: {
          text: `*${ayah.surah.englishName} ${ayah.surah.number}:${ayah.numberInSurah}*\n\n> ${ayah.text}`,
        },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }
}
