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
    let remaining = text.replace(/^\s*,\s*/, '');

    let commandName = '';
    const names = [this.config.name, ...(this.config.aliases || [])];
    for (const name of names) {
      const namePattern = this.replaceDiacritics(name).replace(/\s+/g, '\\s*');
      const match = remaining.match(new RegExp(`^${namePattern}`, 'i'));
      if (match) {
        commandName = name;
        remaining = remaining.slice(match[0].length).trim();
        break;
      }
    }

    const flags = new Set<string>();
    const options = new Map<string, string>();
    const restParts: string[] = [];

    const tokens = remaining.split(/\s+/).filter((t) => t.length > 0);

    for (const token of tokens) {
      let consumed = false;

      for (const opt of this.config.options || []) {
        if (options.has(opt.name)) continue;
        if (opt.values) {
          const matchedValue = opt.values.find((v) => {
            const pattern = this.replaceDiacritics(v);
            return new RegExp(`^${pattern}$`, 'i').test(token);
          });
          if (matchedValue) {
            options.set(opt.name, matchedValue);
            consumed = true;
            break;
          }
        }
        if (opt.pattern && new RegExp(`^${opt.pattern}$`, 'i').test(token)) {
          options.set(opt.name, token);
          consumed = true;
          break;
        }
      }

      if (!consumed) {
        const matchedFlag = (this.config.flags || []).find((f) => {
          if (flags.has(f)) return false;
          const pattern = this.replaceDiacritics(f);
          return new RegExp(`^${pattern}$`, 'i').test(token);
        });
        if (matchedFlag) {
          flags.add(matchedFlag);
          consumed = true;
        }
      }

      if (!consumed) {
        restParts.push(token);
      }
    }

    return {
      commandName,
      flags,
      options,
      rest: restParts.join(' '),
    };
  }

  private buildRegex(): RegExp {
    const parts: string[] = [];

    parts.push('^\\s*,\\s*');

    const names = [this.config.name, ...(this.config.aliases || [])];
    const namePatterns = names.map((n) => this.replaceDiacritics(n).replace(/\s+/g, '\\s*'));
    if (namePatterns.length === 1) {
      parts.push(namePatterns[0]);
    } else {
      parts.push(`(?:${namePatterns.join('|')})`);
    }

    for (const opt of this.config.options || []) {
      if (opt.values) {
        const sorted = [...opt.values].sort((a, b) => b.length - a.length);
        const valPatterns = sorted.map((v) => this.replaceDiacritics(v));
        parts.push(`\\s*(?:${valPatterns.join('|')})?`);
      } else if (opt.pattern) {
        parts.push(`\\s*(?:${opt.pattern})?`);
      }
    }

    for (const flag of this.config.flags || []) {
      parts.push(`\\s*(?:${this.replaceDiacritics(flag)})?`);
    }

    const args = this.config.args ?? ArgType.None;
    switch (args) {
      case ArgType.None:
        parts.push('\\s*$');
        break;
      case ArgType.Required:
        if (this.config.argsPattern) {
          const src = this.config.argsPattern.source.replace(/^\^/, '').replace(/\$$/, '');
          parts.push(`\\s*${src}\\s*$`);
        } else {
          parts.push('\\s+.+');
        }
        break;
      case ArgType.Optional:
        if (this.config.argsPattern) {
          const src = this.config.argsPattern.source.replace(/^\^/, '').replace(/\$$/, '');
          parts.push(`\\s*${src}\\s*$`);
        } else {
          parts.push('(?:\\s+.*)?$');
        }
        break;
    }

    return new RegExp(parts.join(''), 'i');
  }

  private replaceDiacritics(s: string): string {
    return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/[^\x00-\x7F]/g, '.');
  }
}
