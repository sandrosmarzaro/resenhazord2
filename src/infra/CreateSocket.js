import { makeWASocket, fetchLatestWaWebVersion } from '@whiskeysockets/baileys';
import pino from 'pino';
import groupMetadataCache from '../utils/GroupMetadataCache.js';

export default class CreateSocket {
  static async getSocket(state) {
    const { version } = await fetchLatestWaWebVersion();
    const config = {
      auth: state,
      version,
      logger: pino({
        level: 'silent',
      }),
      qrTimeout: 60000,
      syncFullHistory: false,
      markOnlineOnConnect: false,
      generateHighQualityLinkPreview: true,
      cachedGroupMetadata: async (jid) => groupMetadataCache.get(jid),
    };

    return makeWASocket(config);
  }
}
