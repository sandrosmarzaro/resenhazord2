import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import MongoDBConnection from '../../../src/infra/MongoDBConnection.js';
import Resenhazord2 from '../../../src/models/Resenhazord2.js';
import ConnectionWatchdog from '../../../src/infra/ConnectionWatchdog.js';
import CreateAuthState from '../../../src/auth/CreateAuthState.js';
import CreateSocket from '../../../src/infra/CreateSocket.js';

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

  describe('connectToWhatsApp()', () => {
    beforeEach(() => {
      Resenhazord2.isConnecting = false;
    });

    afterEach(() => {
      vi.restoreAllMocks();
    });

    it('arms the watchdog so a socket that never opens forces a restart', async () => {
      const arm = vi.spyOn(ConnectionWatchdog, 'arm').mockImplementation(() => {});
      vi.spyOn(CreateAuthState, 'getAuthState').mockResolvedValue({
        state: {} as never,
        saveCreds: vi.fn(),
      });
      // Minimal socket stub: the adapter constructor only binds updateMediaMessage.
      vi.spyOn(CreateSocket, 'getSocket').mockResolvedValue({
        updateMediaMessage: vi.fn(),
      } as never);
      vi.spyOn(Resenhazord2.broker, 'connect').mockRejectedValue(new Error('no broker'));

      await Resenhazord2.connectToWhatsApp();

      expect(arm).toHaveBeenCalledOnce();
    });
  });
});
