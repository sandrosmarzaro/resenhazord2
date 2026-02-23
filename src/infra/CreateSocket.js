import { makeWASocket } from '@whiskeysockets/baileys';
import pino from 'pino';
import groupMetadataCache from '../utils/GroupMetadataCache.js';

export default class CreateSocket {
  static async getSocket(state) {
    const config = {
      auth: state,
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
