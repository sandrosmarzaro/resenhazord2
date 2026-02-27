import type { CommandData } from '../types/command.js';
import Command from './Command.js';
import Resenhazord2 from '../models/Resenhazord2.js';
import axios from 'axios';

export default class BaralhoCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*carta\\s*(?:show)?\\s*(?:dm)?$';
  readonly menuDescription = 'Receba uma carta de baralho aleatória.';

  async run(data: CommandData): Promise<void> {
    const API_URL = 'https://deckofcardsapi.com/api/deck/new/draw/?count=1';
    try {
      const response = await axios.get(API_URL);
      const card = response.data.cards[0];
      const caption = 'Era essa sua carta? 😏';

      let chat_id: string = data.key.remoteJid!;
      const DM_FLAG_ACTIVE = data.text.match(/dm/);
      if (DM_FLAG_ACTIVE && data.key.participant) {
        chat_id = data.key.participant;
      }
      await Resenhazord2.socket!.sendMessage(
        chat_id,
        { image: { url: card.image }, caption: caption, viewOnce: !data.text.match(/show/) },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
    } catch (error) {
      console.log(`BARALHO COMMAND ERROR\n${error}`);
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `Viiixxiii... Não consegui baixar a carta! 🥺👉👈` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
    }
  }
}
