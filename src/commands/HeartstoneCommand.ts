import type { CommandData } from '../types/command.js';
import Command from './Command.js';
import Resenhazord2 from '../models/Resenhazord2.js';
import axios from 'axios';

export default class HeartstoneCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*hs\\s*(?:show)?\\s*(?:dm)?$';
  readonly menuDescription = 'Receba uma carta aleatória de Hearthstone.';

  async run(data: CommandData): Promise<void> {
    const { BNET_ID, BNET_SECRET } = process.env;
    const access_token = await this.get_access_token(BNET_ID, BNET_SECRET);
    if (!access_token) {
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `Não consegui entrar na Battle.net, manda a Blizzard tomar no cu! 🤷‍♂️` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
      return;
    }

    const api_url = 'https://us.api.blizzard.com/hearthstone/cards?locale=pt_BR';
    try {
      const first_response = await axios.get(api_url, {
        headers: {
          Authorization: `Bearer ${access_token}`,
        },
        params: {
          pageSize: 1,
        },
      });
      const { pageCount } = first_response.data;
      const random_page = Math.floor(Math.random() * pageCount) + 1;

      const response = await axios.get(api_url, {
        headers: {
          Authorization: `Bearer ${access_token}`,
        },
        params: {
          page: random_page,
          pageSize: 1,
        },
      });

      const card = response.data.cards[0];
      let description = card.text.replace(/<\/?b>/g, '*');
      description = description.replace(/<\/?i>/g, '_');
      const caption = `*${card.name}*\n\n> "${card.flavorText}"\n\n${description}`;

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
      console.log(`HEARTHSTONE COMMAND ERROR\n${error}`);
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `Não consegui buscar as cartas do Hearthstone, manda a Blizzard tomar no cu! 🤷‍♂️` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
    }
  }

  private async get_access_token(
    bnet_id: string | undefined,
    bnet_secret: string | undefined,
  ): Promise<string | null> {
    const token_url = 'https://oauth.battle.net/token';
    const auth = Buffer.from(`${bnet_id}:${bnet_secret}`).toString('base64');

    try {
      const response = await axios.post(token_url, 'grant_type=client_credentials', {
        headers: {
          Authorization: `Basic ${auth}`,
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      return response.data.access_token as string;
    } catch (error) {
      console.log(`ERROR HEARTHSTONE COMMAND\n${error}`);
      return null;
    }
  }
}
