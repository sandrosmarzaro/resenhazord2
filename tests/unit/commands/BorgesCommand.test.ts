import { describe, it, expect, beforeEach, vi } from 'vitest';
import BorgesCommand from '../../../src/commands/BorgesCommand.js';
import { GroupCommandData } from '../../fixtures/index.js';
import MongoDBConnection from '../../../src/infra/MongoDBConnection.js';

describe('BorgesCommand', () => {
  let command: BorgesCommand;

  beforeEach(() => {
    command = new BorgesCommand();
    vi.restoreAllMocks();
  });

  describe('matches()', () => {
    it.each([
      [', borges', true],
      [',borges', true],
      [', BORGES', true],
      ['  , borges  ', true],
      ['borges', false],
      ['hello', false],
      [', borges extra', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should increment counter and return formatted message', async () => {
      const findOneAndUpdate = vi.fn().mockResolvedValue({ nargas: 42 });
      vi.spyOn(MongoDBConnection, 'getCollection').mockResolvedValue({
        findOneAndUpdate,
      } as never);

      const data = GroupCommandData.build({ text: ',borges' });

      const messages = await command.run(data);

      expect(findOneAndUpdate).toHaveBeenCalledWith(
        { _id: 'counter' },
        { $inc: { nargas: 1 } },
        { returnDocument: 'after', upsert: true },
      );
      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('42');
      expect(content.text).toContain('nargas');
    });

    it('should quote the original message', async () => {
      const findOneAndUpdate = vi.fn().mockResolvedValue({ nargas: 1 });
      vi.spyOn(MongoDBConnection, 'getCollection').mockResolvedValue({
        findOneAndUpdate,
      } as never);

      const data = GroupCommandData.build({ text: ',borges' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      const findOneAndUpdate = vi.fn().mockResolvedValue({ nargas: 1 });
      vi.spyOn(MongoDBConnection, 'getCollection').mockResolvedValue({
        findOneAndUpdate,
      } as never);

      const data = GroupCommandData.build({ text: ',borges', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });
  });
});
