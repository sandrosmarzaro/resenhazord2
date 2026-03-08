import AxiosClient from '../infra/AxiosClient.js';

const BASE_URL = 'https://discord.com/api/v10';

interface DiscordChannel {
  id: string;
  name: string;
  type: number;
  parent_id?: string;
}

function normalize(name: string): string {
  return name
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .replace(/\s+/g, '-');
}

function nameMatches(channelName: string, searchName: string): boolean {
  const a = channelName.toLowerCase();
  const b = searchName.toLowerCase();
  return a === b || normalize(a) === normalize(b);
}

export default class DiscordService {
  private readonly headers: Record<string, string>;

  constructor(
    private readonly token: string,
    private readonly guildId: string,
  ) {
    this.headers = { Authorization: `Bot ${token}` };
  }

  async getChannels(): Promise<DiscordChannel[]> {
    const response = await AxiosClient.get<DiscordChannel[]>(
      `${BASE_URL}/guilds/${this.guildId}/channels`,
      { headers: this.headers },
    );
    return response.data;
  }

  static findCategory(channels: DiscordChannel[], name: string): DiscordChannel | undefined {
    return channels.find((c) => c.type === 4 && nameMatches(c.name, name));
  }

  static findChannel(
    channels: DiscordChannel[],
    name: string,
    parentId: string,
  ): DiscordChannel | undefined {
    return channels.find(
      (c) => c.type === 0 && nameMatches(c.name, name) && c.parent_id === parentId,
    );
  }

  async createCategory(name: string): Promise<DiscordChannel> {
    const response = await AxiosClient.post<DiscordChannel>(
      `${BASE_URL}/guilds/${this.guildId}/channels`,
      { name: normalize(name), type: 4 },
      { headers: this.headers },
    );
    return response.data;
  }

  async createChannel(name: string, parentId: string): Promise<DiscordChannel> {
    const response = await AxiosClient.post<DiscordChannel>(
      `${BASE_URL}/guilds/${this.guildId}/channels`,
      { name: normalize(name), type: 0, parent_id: parentId },
      { headers: this.headers },
    );
    return response.data;
  }

  async uploadMedia(channelId: string, buffer: Buffer, filename: string): Promise<void> {
    const form = new FormData();
    form.append('files[0]', new Blob([new Uint8Array(buffer)]), filename);

    await AxiosClient.post(`${BASE_URL}/channels/${channelId}/messages`, form, {
      headers: { ...this.headers, 'Content-Type': 'multipart/form-data' },
    });
  }
}
