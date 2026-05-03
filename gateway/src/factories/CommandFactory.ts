import type Command from '../commands/Command.js';

export default class CommandFactory {
  private static instance: CommandFactory | null = null;
  private readonly strategies: Command[] = [];

  static getInstance(): CommandFactory {
    if (!this.instance) {
      this.instance = new CommandFactory();
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
