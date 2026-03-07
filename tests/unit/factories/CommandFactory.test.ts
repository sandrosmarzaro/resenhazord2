import { describe, it, expect, beforeEach } from 'vitest';
import CommandFactory from '../../../src/factories/CommandFactory.js';
import { createMockWhatsAppPort } from '../../fixtures/index.js';

describe('CommandFactory', () => {
  let factory: CommandFactory;

  beforeEach(() => {
    factory = CommandFactory.getInstance();
  });

  describe('getInstance()', () => {
    it('should return the same instance (singleton)', () => {
      const instance1 = CommandFactory.getInstance();
      const instance2 = CommandFactory.getInstance();

      expect(instance1).toBe(instance2);
    });

    it('regression: passes whatsapp adapter to commands that require it', () => {
      CommandFactory.reset();
      const mockWhatsApp = createMockWhatsAppPort();
      const factory = CommandFactory.getInstance(mockWhatsApp);

      const whatsappCommands = [
        'StickerCommand',
        'BanCommand',
        'AddCommand',
        'AdmCommand',
        'ScarraCommand',
      ];
      for (const name of whatsappCommands) {
        const cmd = factory.getAllStrategies().find((c) => c.constructor.name === name);
        expect(cmd, `${name} should be registered`).toBeDefined();
        const whatsapp = (cmd as unknown as { whatsapp: unknown }).whatsapp;
        expect(whatsapp, `${name}.whatsapp should not be undefined`).toBe(mockWhatsApp);
      }

      CommandFactory.reset();
    });
  });

  describe('getStrategy()', () => {
    it.each([
      [', oi', 'OiCommand'],
      [', d20', 'D20Command'],
      [', ban', 'BanCommand'],
      [', menu', 'MenuCommand'],
    ])('should return correct command for "%s"', (input, expectedCommandName) => {
      const command = factory.getStrategy(input);

      expect(command).not.toBeNull();
      expect(command!.constructor.name).toBe(expectedCommandName);
    });

    it('should return null for unknown command', () => {
      const command = factory.getStrategy('unknown command');

      expect(command).toBeNull();
    });

    it('should return null for empty string', () => {
      const command = factory.getStrategy('');

      expect(command).toBeNull();
    });
  });

  describe('getAllStrategies()', () => {
    it('should return all registered commands', () => {
      const strategies = factory.getAllStrategies();

      expect(strategies.length).toBeGreaterThan(0);
    });

    it('should include OiCommand', () => {
      const strategies = factory.getAllStrategies();

      const oiCommand = strategies.find((cmd) => cmd.constructor.name === 'OiCommand');
      expect(oiCommand).not.toBeUndefined();
    });

    it('should include all expected commands', () => {
      const strategies = factory.getAllStrategies();
      const commandNames = strategies.map((cmd) => cmd.constructor.name);

      expect(commandNames).toContain('OiCommand');
      expect(commandNames).toContain('D20Command');
      expect(commandNames).toContain('BanCommand');
      expect(commandNames).toContain('MenuCommand');
    });
  });
});
