import { ArgType } from '../types/commandConfig.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';

export default class CommandParser {
  private readonly regex: RegExp;

  constructor(private readonly config: CommandConfig) {
    this.regex = this.buildRegex();
  }

  matches(text: string): boolean {
    return this.regex.test(text);
  }

  parse(text: string): ParsedCommand {
    const { commandName, remaining } = this.extractCommandName(text.replace(/^\s*,\s*/, ''));

    const tokens = remaining.split(/\s+/).filter((t) => t.length > 0);
    const flags = new Set<string>();
    const options = new Map<string, string>();
    const restParts: string[] = [];

    for (const token of tokens) {
      if (this.tryMatchOption(token, options)) continue;
      if (this.tryMatchFlag(token, flags)) continue;
      restParts.push(token);
    }

    return { commandName, flags, options, rest: restParts.join(' ') };
  }

  private extractCommandName(remaining: string): { commandName: string; remaining: string } {
    const names = [this.config.name, ...(this.config.aliases || [])];
    for (const name of names) {
      const namePattern = this.replaceDiacritics(name).replaceAll(/\s+/g, String.raw`\s*`);
      const match = new RegExp(`^${namePattern}`, 'i').exec(remaining);
      if (match) {
        return { commandName: name, remaining: remaining.slice(match[0].length).trim() };
      }
    }
    return { commandName: '', remaining };
  }

  private tryMatchOption(token: string, options: Map<string, string>): boolean {
    for (const opt of this.config.options || []) {
      if (options.has(opt.name)) continue;
      if (opt.values) {
        const matchedValue = opt.values.find((v) =>
          new RegExp(`^${this.replaceDiacritics(v)}$`, 'i').test(token),
        );
        if (matchedValue) {
          options.set(opt.name, matchedValue);
          return true;
        }
      }
      if (opt.pattern && new RegExp(`^${opt.pattern}$`, 'i').test(token)) {
        options.set(opt.name, token);
        return true;
      }
    }
    return false;
  }

  private tryMatchFlag(token: string, flags: Set<string>): boolean {
    const matchedFlag = (this.config.flags || []).find((f) => {
      if (flags.has(f)) return false;
      return new RegExp(`^${this.replaceDiacritics(f)}$`, 'i').test(token);
    });
    if (matchedFlag) {
      flags.add(matchedFlag);
      return true;
    }
    return false;
  }

  private buildRegex(): RegExp {
    const parts: string[] = [];

    parts.push(String.raw`^\s*,\s*`);

    const names = [this.config.name, ...(this.config.aliases || [])];
    const namePatterns = names.map((n) =>
      this.replaceDiacritics(n).replaceAll(/\s+/g, String.raw`\s*`),
    );
    if (namePatterns.length === 1) {
      parts.push(namePatterns[0]);
    } else {
      parts.push(`(?:${namePatterns.join('|')})`);
    }

    for (const opt of this.config.options || []) {
      if (opt.values) {
        const sorted = [...opt.values].sort((a, b) => b.length - a.length);
        const valPatterns = sorted.map((v) => this.replaceDiacritics(v));
        parts.push(String.raw`\s*(?:${valPatterns.join('|')})?`);
      } else if (opt.pattern) {
        parts.push(String.raw`\s*(?:${opt.pattern})?`);
      }
    }

    if (this.config.flags && this.config.flags.length > 0) {
      const flagPatterns = this.config.flags.map((f) => this.replaceDiacritics(f));
      parts.push(String.raw`(?:\s+(?:${flagPatterns.join('|')}))*`);
    }

    const args = this.config.args ?? ArgType.None;
    switch (args) {
      case ArgType.None:
        parts.push(String.raw`\s*$`);
        break;
      case ArgType.Required:
        if (this.config.argsPattern) {
          const src = this.config.argsPattern.source.replace(/^\^/, '').replace(/\$$/, '');
          parts.push(String.raw`\s*${src}\s*$`);
        } else {
          parts.push(String.raw`\s+.+`);
        }
        break;
      case ArgType.Optional:
        if (this.config.argsPattern) {
          const src = this.config.argsPattern.source.replace(/^\^/, '').replace(/\$$/, '');
          parts.push(String.raw`\s*${src}\s*$`);
        } else {
          parts.push(String.raw`(?:\s+.*)?$`);
        }
        break;
    }

    return new RegExp(parts.join(''), 'i');
  }

  private replaceDiacritics(s: string): string {
    return s.replaceAll(/[.*+?^${}()|[\]\\]/g, String.raw`\$&`).replaceAll(/[^\x00-\x7F]/g, '.');
  }
}
