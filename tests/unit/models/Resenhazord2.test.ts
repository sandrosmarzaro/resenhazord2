import { describe, it, expect, vi, beforeEach } from 'vitest';
import MongoDBConnection from '../../../src/infra/MongoDBConnection.js';
import Resenhazord2 from '../../../src/models/Resenhazord2.js';

describe('Resenhazord2', () => {
  describe('cleanup()', () => {
    beforeEach(() => {
      Resenhazord2.isConnecting = false;
    });

    it('regression: does not close MongoDB during WhatsApp reconnection cleanup', async () => {
      const closeSpy = vi.spyOn(MongoDBConnection, 'close');

      await Resenhazord2.cleanup();

      expect(closeSpy).not.toHaveBeenCalled();
    });
  });
});
