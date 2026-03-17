import type Command from '../commands/Command.js';
import type WhatsAppPort from '../ports/WhatsAppPort.js';

import AddCommand from '../commands/AddCommand.js';
import AnimalCommand from '../commands/AnimalCommand.js';
import AdmCommand from '../commands/AdmCommand.js';
import DriveCommand from '../commands/DriveCommand.js';
import ExtrairCommand from '../commands/ExtrairCommand.js';
import AudioCommand from '../commands/AudioCommand.js';
import BanCommand from '../commands/BanCommand.js';
import BorgesCommand from '../commands/BorgesCommand.js';
import CarroCommand from '../commands/CarroCommand.js';
import DownloadCommand from '../commands/DownloadCommand.js';
import GameCommand from '../commands/GameCommand.js';
import GroupMentionsCommand from '../commands/GroupMentionsCommand.js';
import HeartstoneCommand from '../commands/HeartstoneCommand.js';
import MagicTheGatheringCommand from '../commands/MagicTheGatheringCommand.js';
import PokemonTCGCommand from '../commands/PokemonTCGCommand.js';
import MusicCommand from '../commands/MusicCommand.js';
import MenuCommand from '../commands/MenuCommand.js';
import PokemonCommand from '../commands/PokemonCommand.js';
import HentaiCommand from '../commands/HentaiCommand.js';
import ScarraCommand from '../commands/ScarraCommand.js';
import StickerCommand from '../commands/StickerCommand.js';
import YugiohCommand from '../commands/YugiohCommand.js';
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
      new AddCommand(whatsapp),
      new AdmCommand(whatsapp),
      new AnimalCommand(),
      new AudioCommand(),
      new BanCommand(whatsapp),
      new BorgesCommand(),
      new CarroCommand(),
      new DownloadCommand(),
      new DriveCommand(whatsapp, discordService),
      new ExtrairCommand(whatsapp),
      new GameCommand(),
      new GroupMentionsCommand(),
      new HeartstoneCommand(),
      new MagicTheGatheringCommand(),
      new MusicCommand(),
      new MenuCommand(),
      new PokemonCommand(),
      new PokemonTCGCommand(),
      new HentaiCommand(),
      new ScarraCommand(whatsapp),
      new StickerCommand(whatsapp),
      new YugiohCommand(),
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
