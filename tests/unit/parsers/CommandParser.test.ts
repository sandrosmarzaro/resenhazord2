import CommandParser from '../../../src/parsers/CommandParser.js';
import { ArgType } from '../../../src/types/commandConfig.js';
import type { CommandConfig } from '../../../src/types/commandConfig.js';

describe('CommandParser', () => {
  describe('simple command (no flags/options/args)', () => {
    const config: CommandConfig = { name: 'oi' };
    let parser: CommandParser;

    beforeEach(() => {
      parser = new CommandParser(config);
    });

    describe('matches()', () => {
      it.each([
        [', oi', true],
        [',oi', true],
        [', OI', true],
        ['  , oi  ', true],
        ['\t,\toi\t', true],
        ['oi', false],
        [', oi test', false],
        [', oie', false],
      ])('should return %s for "%s"', (input, expected) => {
        expect(parser.matches(input as string)).toBe(expected);
      });
    });

    describe('parse()', () => {
      it('should parse simple command', () => {
        const result = parser.parse(', oi');
        expect(result.commandName).toBe('oi');
        expect(result.flags.size).toBe(0);
        expect(result.options.size).toBe(0);
        expect(result.rest).toBe('');
      });
    });
  });

  describe('command with diacritics', () => {
    const config: CommandConfig = { name: 'pokémon', flags: ['team', 'show', 'dm'] };
    let parser: CommandParser;

    beforeEach(() => {
      parser = new CommandParser(config);
    });

    describe('matches()', () => {
      it.each([
        [',pokémon', true],
        [',pokemon', true],
        [',pokémon team', true],
        [',pokémon show dm', true],
        [',pokémon team show dm', true],
        [',pokemon team show dm', true],
        [',pokémon hello', false],
      ])('should return %s for "%s"', (input, expected) => {
        expect(parser.matches(input as string)).toBe(expected);
      });
    });

    describe('parse()', () => {
      it('should parse flags', () => {
        const result = parser.parse(',pokémon team show dm');
        expect(result.commandName).toBe('pokémon');
        expect(result.flags).toEqual(new Set(['team', 'show', 'dm']));
        expect(result.rest).toBe('');
      });

      it('should parse partial flags', () => {
        const result = parser.parse(',pokémon show');
        expect(result.flags).toEqual(new Set(['show']));
      });

      it('should parse no flags', () => {
        const result = parser.parse(',pokémon');
        expect(result.flags.size).toBe(0);
      });
    });
  });

  describe('command with aliases', () => {
    const config: CommandConfig = {
      name: 'anime',
      aliases: ['manga'],
      flags: ['show', 'dm'],
    };
    let parser: CommandParser;

    beforeEach(() => {
      parser = new CommandParser(config);
    });

    describe('matches()', () => {
      it.each([
        [',anime', true],
        [',manga', true],
        [',anime show', true],
        [',manga dm', true],
        [',anime show dm', true],
        [',animee', false],
      ])('should return %s for "%s"', (input, expected) => {
        expect(parser.matches(input as string)).toBe(expected);
      });
    });

    describe('parse()', () => {
      it('should record anime as commandName', () => {
        const result = parser.parse(',anime show');
        expect(result.commandName).toBe('anime');
        expect(result.flags).toEqual(new Set(['show']));
      });

      it('should record manga as commandName', () => {
        const result = parser.parse(',manga dm');
        expect(result.commandName).toBe('manga');
        expect(result.flags).toEqual(new Set(['dm']));
      });
    });
  });

  describe('command with options', () => {
    const config: CommandConfig = {
      name: 'stic',
      options: [{ name: 'type', values: ['crop', 'full', 'circle', 'rounded'] }],
    };
    let parser: CommandParser;

    beforeEach(() => {
      parser = new CommandParser(config);
    });

    describe('matches()', () => {
      it.each([
        [',stic', true],
        [',stic crop', true],
        [',stic full', true],
        [',stic circle', true],
        [',stic rounded', true],
        [',stic hello', false],
      ])('should return %s for "%s"', (input, expected) => {
        expect(parser.matches(input as string)).toBe(expected);
      });
    });

    describe('parse()', () => {
      it('should parse option value', () => {
        const result = parser.parse(',stic crop');
        expect(result.options.get('type')).toBe('crop');
      });

      it('should have no option when not provided', () => {
        const result = parser.parse(',stic');
        expect(result.options.size).toBe(0);
      });
    });
  });

  describe('command with options + flags + args', () => {
    const config: CommandConfig = {
      name: 'img',
      options: [
        { name: 'resolution', values: ['sd', 'hd', 'fhd', 'qhd', '4k'] },
        {
          name: 'model',
          values: ['flux-pro', 'flux-realism', 'flux-anime', 'flux-3d', 'flux', 'cablyai', 'turbo'],
        },
      ],
      flags: ['show', 'dm'],
      args: ArgType.Optional,
    };
    let parser: CommandParser;

    beforeEach(() => {
      parser = new CommandParser(config);
    });

    describe('matches()', () => {
      it.each([
        [',img', true],
        [',img hd', true],
        [',img hd flux-pro a cat', true],
        [',img show dm a cat', true],
        [',img 4k turbo show dm a beautiful sunset', true],
      ])('should return %s for "%s"', (input, expected) => {
        expect(parser.matches(input as string)).toBe(expected);
      });
    });

    describe('parse()', () => {
      it('should parse options, flags, and rest', () => {
        const result = parser.parse(',img hd flux-pro show dm a beautiful cat');
        expect(result.options.get('resolution')).toBe('hd');
        expect(result.options.get('model')).toBe('flux-pro');
        expect(result.flags).toEqual(new Set(['show', 'dm']));
        expect(result.rest).toBe('a beautiful cat');
      });

      it('should handle only prompt text', () => {
        const result = parser.parse(',img a beautiful cat');
        expect(result.options.size).toBe(0);
        expect(result.flags.size).toBe(0);
        expect(result.rest).toBe('a beautiful cat');
      });

      it('should handle no args', () => {
        const result = parser.parse(',img');
        expect(result.rest).toBe('');
      });
    });
  });

  describe('command with pattern option', () => {
    const config: CommandConfig = {
      name: 'áudio',
      options: [{ name: 'lang', pattern: '[A-Za-z]{2}-[A-Za-z]{2}' }],
      flags: ['show', 'dm'],
      args: ArgType.Optional,
    };
    let parser: CommandParser;

    beforeEach(() => {
      parser = new CommandParser(config);
    });

    describe('matches()', () => {
      it.each([
        [',áudio', true],
        [',audio', true],
        [',áudio pt-BR hello', true],
        [',audio en-US show dm hello', true],
      ])('should return %s for "%s"', (input, expected) => {
        expect(parser.matches(input as string)).toBe(expected);
      });
    });

    describe('parse()', () => {
      it('should parse pattern option', () => {
        const result = parser.parse(',áudio pt-BR hello world');
        expect(result.options.get('lang')).toBe('pt-BR');
        expect(result.rest).toBe('hello world');
      });

      it('should default when no lang provided', () => {
        const result = parser.parse(',áudio hello world');
        expect(result.options.size).toBe(0);
        expect(result.rest).toBe('hello world');
      });
    });
  });

  describe('command with name containing space', () => {
    const config: CommandConfig = { name: 'rule 34', flags: ['show', 'dm'] };
    let parser: CommandParser;

    beforeEach(() => {
      parser = new CommandParser(config);
    });

    describe('matches()', () => {
      it.each([
        [',rule 34', true],
        [',rule 34 show', true],
        [',rule 34 show dm', true],
        [', rule 34', true],
        [',rule34', true],
        [',rule', false],
      ])('should return %s for "%s"', (input, expected) => {
        expect(parser.matches(input as string)).toBe(expected);
      });
    });

    describe('parse()', () => {
      it('should parse correctly', () => {
        const result = parser.parse(',rule 34 show dm');
        expect(result.commandName).toBe('rule 34');
        expect(result.flags).toEqual(new Set(['show', 'dm']));
      });
    });
  });

  describe('command with argsPattern', () => {
    const config: CommandConfig = {
      name: 'ban',
      args: ArgType.Optional,
      argsPattern: /^(?:@\d+\s*)*$/,
      groupOnly: true,
    };
    let parser: CommandParser;

    beforeEach(() => {
      parser = new CommandParser(config);
    });

    describe('matches()', () => {
      it.each([
        [',ban', true],
        [',ban @123', true],
        [',ban @123 @456', true],
        [',ban hello', false],
      ])('should return %s for "%s"', (input, expected) => {
        expect(parser.matches(input as string)).toBe(expected);
      });
    });
  });

  describe('command with groupOnly', () => {
    const config: CommandConfig = { name: 'adm', groupOnly: true };
    let parser: CommandParser;

    beforeEach(() => {
      parser = new CommandParser(config);
    });

    it('should still match text (groupOnly is enforced at runtime)', () => {
      expect(parser.matches(',adm')).toBe(true);
    });
  });

  describe('command with required args', () => {
    const config: CommandConfig = {
      name: 'fuck',
      args: ArgType.Required,
      argsPattern: /^@\d+\s*$/,
      groupOnly: true,
    };
    let parser: CommandParser;

    beforeEach(() => {
      parser = new CommandParser(config);
    });

    describe('matches()', () => {
      it.each([
        [',fuck @123', true],
        [',fuck', false],
        [',fuck hello', false],
      ])('should return %s for "%s"', (input, expected) => {
        expect(parser.matches(input as string)).toBe(expected);
      });
    });
  });

  describe('command with multiple options + args', () => {
    const config: CommandConfig = {
      name: 'bíblia',
      options: [
        { name: 'lang', values: ['pt', 'en'] },
        { name: 'version', values: ['nvi', 'ra', 'acf', 'kjv', 'bbe', 'apee', 'rvr'] },
      ],
      args: ArgType.Optional,
    };
    let parser: CommandParser;

    beforeEach(() => {
      parser = new CommandParser(config);
    });

    describe('matches()', () => {
      it.each([
        [',bíblia', true],
        [',biblia', true],
        [',bíblia pt nvi', true],
        [',biblia en kjv Genesis 1:1', true],
      ])('should return %s for "%s"', (input, expected) => {
        expect(parser.matches(input as string)).toBe(expected);
      });
    });

    describe('parse()', () => {
      it('should parse lang, version, and verse reference', () => {
        const result = parser.parse(',bíblia pt nvi Genesis 1:1');
        expect(result.options.get('lang')).toBe('pt');
        expect(result.options.get('version')).toBe('nvi');
        expect(result.rest).toBe('Genesis 1:1');
      });

      it('should handle no options', () => {
        const result = parser.parse(',bíblia');
        expect(result.options.size).toBe(0);
        expect(result.rest).toBe('');
      });
    });
  });
});
