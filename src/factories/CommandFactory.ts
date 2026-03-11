import type Command from '../commands/Command.js';
import type WhatsAppPort from '../ports/WhatsAppPort.js';

import AddCommand from '../commands/AddCommand.js';
import AnimalCommand from '../commands/AnimalCommand.js';
import AdmCommand from '../commands/AdmCommand.js';
import DriveCommand from '../commands/DriveCommand.js';
import ExtrairCommand from '../commands/ExtrairCommand.js';
import AlcoranCommand from '../commands/AlcoranCommand.js';
import AudioCommand from '../commands/AudioCommand.js';
import BanCommand from '../commands/BanCommand.js';
import BaralhoCommand from '../commands/BaralhoCommand.js';
import BeerCommand from '../commands/BeerCommand.js';
import BichoCommand from '../commands/BichoCommand.js';
import BibliaCommand from '../commands/BibliaCommand.js';
import BorgesCommand from '../commands/BorgesCommand.js';
import ClashRoyaleCommand from '../commands/ClashRoyaleCommand.js';
import CountryFlagCommand from '../commands/CountryFlagCommand.js';
import D20Command from '../commands/D20Command.js';
import DownloadCommand from '../commands/DownloadCommand.js';
import FatoCommand from '../commands/FatoCommand.js';
import FilmeSerieCommand from '../commands/FilmeSerieCommand.js';
import GameCommand from '../commands/GameCommand.js';
import FuckCommand from '../commands/FuckCommand.js';
import GroupMentionsCommand from '../commands/GroupMentionsCommand.js';
import HeartstoneCommand from '../commands/HeartstoneCommand.js';
import LeagueOfLegendsCommand from '../commands/LeagueOfLegendsCommand.js';
import MagicTheGatheringCommand from '../commands/MagicTheGatheringCommand.js';
import PokemonTCGCommand from '../commands/PokemonTCGCommand.js';
import MateusCommand from '../commands/MateusCommand.js';
import MealRecipesCommand from '../commands/MealRecipesCommand.js';
import MusicCommand from '../commands/MusicCommand.js';
import MenuCommand from '../commands/MenuCommand.js';
import MyAnimeListCommand from '../commands/MyAnimeListCommand.js';
import OiCommand from '../commands/OiCommand.js';
import PokemonCommand from '../commands/PokemonCommand.js';
import PornoCommand from '../commands/PornoCommand.js';
import Rule34Command from '../commands/Rule34Command.js';
import ScarraCommand from '../commands/ScarraCommand.js';
import StickerCommand from '../commands/StickerCommand.js';
import YugiohCommand from '../commands/YugiohCommand.js';
import DiscordService from '../services/DiscordService.js';

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
      new AlcoranCommand(),
      new AnimalCommand(),
      new AudioCommand(),
      new BanCommand(whatsapp),
      new BaralhoCommand(),
      new BeerCommand(),
      new BichoCommand(),
      new BibliaCommand(),
      new BorgesCommand(),
      new ClashRoyaleCommand(),
      new CountryFlagCommand(),
      new D20Command(),
      new DownloadCommand(),
      new DriveCommand(whatsapp, discordService),
      new ExtrairCommand(whatsapp),
      new FatoCommand(),
      new FilmeSerieCommand(),
      new FuckCommand(),
      new GameCommand(),
      new GroupMentionsCommand(),
      new HeartstoneCommand(),
      new LeagueOfLegendsCommand(),
      new MagicTheGatheringCommand(),
      new MateusCommand(),
      new MealRecipesCommand(),
      new MusicCommand(),
      new MenuCommand(),
      new MyAnimeListCommand(),
      new OiCommand(),
      new PokemonCommand(),
      new PokemonTCGCommand(),
      new PornoCommand(),
      new Rule34Command(),
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
