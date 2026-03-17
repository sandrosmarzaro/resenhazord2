import Command, { type CommandData, type Message } from './Command.js';
import type { GridOptions } from '../services/CardGridBuilder.js';
import Reply from '../builders/Reply.js';
import AxiosClient from '../infra/AxiosClient.js';
import { buildCardGrid } from '../services/CardGridBuilder.js';

export interface BoosterConfig extends GridOptions {
  flagName: string;
  count: number;
}

export interface CardItem {
  imageUrl: string;
  label: string;
}

export default abstract class CardBoosterCommand extends Command {
  protected abstract readonly boosterConfig: BoosterConfig;

  protected abstract fetchBoosterItems(): Promise<CardItem[]>;

  protected async runBooster(data: CommandData): Promise<Message[]> {
    const items = await this.fetchBoosterItems();
    const imageBuffers = await Promise.all(
      items.map((item) => AxiosClient.getBuffer(item.imageUrl)),
    );
    const gridBuffer = await buildCardGrid(imageBuffers, this.boosterConfig);
    const caption = items.map((item, i) => `*${i + 1}.* ${item.label}`).join('\n\n');
    return [Reply.to(data).imageBuffer(gridBuffer, caption)];
  }
}
