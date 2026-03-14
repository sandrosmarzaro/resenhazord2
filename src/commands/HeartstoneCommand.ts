import CardBoosterCommand, { type BoosterConfig, type CardItem } from './CardBoosterCommand.js';
import {
  type CommandData,
  type CommandConfig,
  type ParsedCommand,
  type Message,
} from './Command.js';
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

export default class HeartstoneCommand extends CardBoosterCommand {
  readonly config: CommandConfig = {
    name: 'hs',
    flags: ['booster', 'show', 'dm'],
    category: 'aleatórias',
  };
  readonly menuDescription = 'Receba uma carta aleatória de Hearthstone.';

  protected readonly boosterConfig: BoosterConfig = {
    flagName: 'booster',
    count: 6,
    columns: 3,
    cellWidth: 300,
    cellHeight: 420,
    shim: 0,
    shimBackground: '#ffffff',
    background: { r: 0, g: 0, b: 0, alpha: 0 },
  };

  private static readonly API_URL = 'https://us.api.blizzard.com/hearthstone/cards?locale=pt_BR';
  private static cachedToken: string | null = null;

  protected async execute(data: CommandData, parsed: ParsedCommand): Promise<Message[]> {
    if (parsed.flags.has('booster')) {
      return this.runBooster(data);
    }

    const { BNET_ID, BNET_SECRET } = process.env;
    const access_token = await this.get_access_token(BNET_ID, BNET_SECRET);
    if (!access_token) {
      return [
        Reply.to(data).text(`Não consegui entrar na Battle.net, manda a Blizzard tomar no cu! 🤷‍♂️`),
      ];
    }

    const api_url = HeartstoneCommand.API_URL;
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

  protected async fetchBoosterItems(): Promise<CardItem[]> {
    const { BNET_ID, BNET_SECRET } = process.env;
    const access_token = await this.get_access_token(BNET_ID, BNET_SECRET);
    if (!access_token) throw new Error('Hearthstone: OAuth token unavailable');

    const api_url = HeartstoneCommand.API_URL;
    const authHeaders = { Authorization: `Bearer ${access_token}` };

    const first_response = await AxiosClient.get<HearthstoneResponse>(api_url, {
      headers: authHeaders,
      params: { pageSize: 1 },
    });
    const { pageCount } = first_response.data;

    const responses = await Promise.all(
      Array.from({ length: this.boosterConfig.count }, () => {
        const random_page = Math.floor(Math.random() * pageCount) + 1;
        return AxiosClient.get<HearthstoneResponse>(api_url, {
          headers: authHeaders,
          params: { page: random_page, pageSize: 1 },
        });
      }),
    );

    return responses.map((r) => {
      const card = r.data.cards[0];
      return { imageUrl: card.image, label: card.name };
    });
  }

  private async get_access_token(
    bnet_id: string | undefined,
    bnet_secret: string | undefined,
  ): Promise<string | null> {
    if (HeartstoneCommand.cachedToken) return HeartstoneCommand.cachedToken;

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

      HeartstoneCommand.cachedToken = response.data.access_token;
      return HeartstoneCommand.cachedToken;
    } catch (error) {
      console.log(`ERROR HEARTHSTONE COMMAND\n${error}`);
      return null;
    }
  }
}
