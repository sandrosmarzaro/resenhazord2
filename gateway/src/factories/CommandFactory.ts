import type Command from '../commands/Command.js';
import type WhatsAppPort from '../ports/WhatsAppPort.js';

import DriveCommand from '../commands/DriveCommand.js';
import ExtrairCommand from '../commands/ExtrairCommand.js';
import ScarraCommand from '../commands/ScarraCommand.js';
import StickerCommand from '../commands/StickerCommand.js';
import DiscordService from '../clients/DiscordService.js';

export default class CommandFactory {
  private static instance: CommandFactory | null = null;
  private readonly strategies: Command[];

  private constructor(whatsapp?: WhatsAppPort) {
    const discordService =
      process.env.DISCORD_TOKEN && process.env.DISCORD_GUILD_ID
        ? new DiscordService(process.env.DISCORD_TOKEN, process.env.DISCORD_GUILD_ID)
        : undefined;

    this.strategies = [
      new DriveCommand(whatsapp, discordService),
      new ExtrairCommand(whatsapp),
      new ScarraCommand(whatsapp),
      new StickerCommand(whatsapp),
    ];
  }

  static getInstance(whatsapp?: WhatsAppPort): CommandFactory {
    if (!this.instance) {
      this.instance = new CommandFactory(whatsapp);
    }
    return this.instance;
  }

  static reset(): void {
    this.instance = null;
  }

  getStrategy(text: string): Command | null {
    return this.strategies.find((cmd) => cmd.matches(text)) ?? null;
  }

  getAllStrategies(): Command[] {
    return this.strategies;
  }
}
