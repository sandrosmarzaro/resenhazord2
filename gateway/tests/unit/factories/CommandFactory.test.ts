import { describe, it, expect, beforeEach } from 'vitest';
import CommandFactory from '../../../src/factories/CommandFactory.js';

describe('CommandFactory', () => {
  let factory: CommandFactory;

  beforeEach(() => {
    CommandFactory.reset();
    factory = CommandFactory.getInstance();
  });

  describe('getInstance()', () => {
    it('should return the same instance (singleton)', () => {
      const instance1 = CommandFactory.getInstance();
      const instance2 = CommandFactory.getInstance();

      expect(instance1).toBe(instance2);
    });
  });

  describe('getStrategy()', () => {
    it('should return null for any input (all commands migrated to Python)', () => {
      expect(factory.getStrategy(', stic')).toBeNull();
      expect(factory.getStrategy(', extrair')).toBeNull();
      expect(factory.getStrategy(', scarra')).toBeNull();
      expect(factory.getStrategy(', drive 2026 foo')).toBeNull();
    });

    it('should return null for empty string', () => {
      expect(factory.getStrategy('')).toBeNull();
    });
  });

  describe('getAllStrategies()', () => {
    it('should return empty array (all commands migrated to Python)', () => {
      expect(factory.getAllStrategies()).toHaveLength(0);
    });
  });
});
