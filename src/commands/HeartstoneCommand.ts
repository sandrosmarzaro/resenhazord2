import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import AxiosClient from '../infra/AxiosClient.js';
import Reply from '../builders/Reply.js';

interface HearthstoneCard {
  name: string;
  text: string;
  flavorText: string;
  image: string;
}

interface HearthstoneResponse {
  pageCount: number;
  cards: HearthstoneCard[];
}

export default class HeartstoneCommand extends Command {
  readonly config: CommandConfig = { name: 'hs', flags: ['show', 'dm'] };
  readonly menuDescription = 'Receba uma carta aleatória de Hearthstone.';

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
    const { BNET_ID, BNET_SECRET } = process.env;
    const access_token = await this.get_access_token(BNET_ID, BNET_SECRET);
    if (!access_token) {
      return [
        Reply.to(data).text(`Não consegui entrar na Battle.net, manda a Blizzard tomar no cu! 🤷‍♂️`),
      ];
    }

    const api_url = 'https://us.api.blizzard.com/hearthstone/cards?locale=pt_BR';
    const first_response = await AxiosClient.get<HearthstoneResponse>(api_url, {
      headers: {
        Authorization: `Bearer ${access_token}`,
      },
      params: {
        pageSize: 1,
      },
    });
    const { pageCount } = first_response.data;
    const random_page = Math.floor(Math.random() * pageCount) + 1;

    const response = await AxiosClient.get<HearthstoneResponse>(api_url, {
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

    return [Reply.to(data).image(card.image, caption)];
  }

  private async get_access_token(
    bnet_id: string | undefined,
    bnet_secret: string | undefined,
  ): Promise<string | null> {
    const token_url = 'https://oauth.battle.net/token';
    const auth = Buffer.from(`${bnet_id}:${bnet_secret}`).toString('base64');

    try {
      const response = await AxiosClient.post<{ access_token: string }>(
        token_url,
        'grant_type=client_credentials',
        {
          headers: {
            Authorization: `Basic ${auth}`,
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        },
      );

      return response.data.access_token;
    } catch (error) {
      console.log(`ERROR HEARTHSTONE COMMAND\n${error}`);
      return null;
    }
  }
}
