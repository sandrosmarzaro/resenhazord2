import type Command from '../commands/Command.js';
import type WhatsAppPort from '../ports/WhatsAppPort.js';

import AddCommand from '../commands/AddCommand.js';
import AdmCommand from '../commands/AdmCommand.js';
import AlcoranCommand from '../commands/AlcoranCommand.js';
import AudioCommand from '../commands/AudioCommand.js';
import BanCommand from '../commands/BanCommand.js';
import BaralhoCommand from '../commands/BaralhoCommand.js';
import BeerCommand from '../commands/BeerCommand.js';
import BibliaCommand from '../commands/BibliaCommand.js';
import BorgesCommand from '../commands/BorgesCommand.js';
import D20Command from '../commands/D20Command.js';
import FatoCommand from '../commands/FatoCommand.js';
import FilmeSerieCommand from '../commands/FilmeSerieCommand.js';
import FuckCommand from '../commands/FuckCommand.js';
import GroupMentionsCommand from '../commands/GroupMentionsCommand.js';
import HeartstoneCommand from '../commands/HeartstoneCommand.js';
import LeagueOfLegendsCommand from '../commands/LeagueOfLegendsCommand.js';
import MagicTheGatheringCommand from '../commands/MagicTheGatheringCommand.js';
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

export default class CommandFactory {
  private static instance: CommandFactory | null = null;
  private readonly strategies: Command[];

  private constructor(whatsapp?: WhatsAppPort) {
    this.strategies = [
      new AddCommand(whatsapp),
      new AdmCommand(whatsapp),
      new AlcoranCommand(),
      new AudioCommand(),
      new BanCommand(whatsapp),
      new BaralhoCommand(),
      new BeerCommand(),
      new BibliaCommand(),
      new BorgesCommand(),
      new D20Command(),
      new FatoCommand(),
      new FilmeSerieCommand(),
      new FuckCommand(),
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
