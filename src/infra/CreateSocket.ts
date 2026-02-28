import type { AuthenticationState, WASocket } from '@whiskeysockets/baileys';
import { makeWASocket, fetchLatestWaWebVersion } from '@whiskeysockets/baileys';
import pino from 'pino';
import groupMetadataCache from '../utils/GroupMetadataCache.js';

const QR_CODE_TIMEOUT = 60000;

export default class CreateSocket {
  static async getSocket(state: AuthenticationState): Promise<WASocket> {
    const { version } = await fetchLatestWaWebVersion();
    const config = {
      auth: state,
      version,
      logger: pino({
        level: 'silent',
      }),
      qrTimeout: QR_CODE_TIMEOUT,
      syncFullHistory: false,
      markOnlineOnConnect: false,
      generateHighQualityLinkPreview: true,
      cachedGroupMetadata: async (jid: string) => groupMetadataCache.get(jid),
    };

    return makeWASocket(config);
  }
}
