import type { WASocket, BaileysEventMap } from '@whiskeysockets/baileys';
import type { MongoDBAuthResult } from '../auth/MongoDBAuthState.js';
import type WhatsAppPort from '../ports/WhatsAppPort.js';
import CreateSocket from '../infra/CreateSocket.js';
import CreateAuthState from '../auth/CreateAuthState.js';
import BaileysAdapter from '../adapters/BaileysAdapter.js';
import MessageUpsertEvent from '../events/MessageUpsertEvent.js';
import ConnectionUpdateEvent from '../events/ConnectionUpdateEvent.js';
import GroupParticipantsUpdateEvent from '../events/GroupParticipantsUpdateEvent.js';
import groupMetadataCache from '../cache/index.js';
import CommandFactory from '../factories/CommandFactory.js';
import PythonBridge from '../bridge/PythonBridge.js';
import { Sentry } from '../infra/Sentry.js';
import logger from '../infra/Logger.js';

export default class Resenhazord2 {
  static auth_state: MongoDBAuthResult | null = null;
  private static socket: WASocket | null = null;
  static adapter: WhatsAppPort | null = null;
  static bridge: PythonBridge = new PythonBridge();
  static isConnecting = false;

  static async connectToWhatsApp(): Promise<void> {
    if (this.isConnecting) {
      logger.info({ event: 'connection_already_in_progress' });
      return;
    }
    this.isConnecting = true;
    try {
      this.auth_state = await CreateAuthState.getAuthState();
      this.socket = await CreateSocket.getSocket(this.auth_state.state);
      this.adapter = new BaileysAdapter(this.socket);
      this.bridge.setWhatsApp(this.adapter);
      this.bridge.connect();
      logger.info({ event: 'socket_created' });
    } catch (error) {
      Sentry.captureException(error);
      logger.error({ event: 'connection_failed', error: (error as Error).message });
      throw error;
    } finally {
      this.isConnecting = false;
    }
  }

  static async onConnectionUpdate(update: BaileysEventMap['connection.update']): Promise<void> {
    await ConnectionUpdateEvent.run(update);
  }

  static async onMessagesUpsert(data: BaileysEventMap['messages.upsert']): Promise<void> {
    await MessageUpsertEvent.run(data);
  }

  static async onGroupsUpsert(groups: BaileysEventMap['groups.upsert']): Promise<void> {
    for (const group of groups) {
      await groupMetadataCache.set(group.id, group);
    }
  }

  static async onGroupParticipantsUpdate(
    data: BaileysEventMap['group-participants.update'],
  ): Promise<void> {
    try {
      const meta = await Resenhazord2.adapter!.groupMetadata(data.id);
      await groupMetadataCache.set(data.id, meta);
    } catch (error) {
      logger.warn({ event: 'group_metadata_cache_update_failed', error: String(error) });
    }
    await GroupParticipantsUpdateEvent.run(data);
  }

  static async handlerEvents(): Promise<void> {
    if (!this.socket) {
      logger.error({ event: 'handler_setup_failed', reason: 'socket_is_null' });
      return;
    }
    this.socket.ev.removeAllListeners('connection.update');

    await this.socket.ev.on('connection.update', this.onConnectionUpdate);
    await this.socket.ev.on('messages.upsert', this.onMessagesUpsert);
    await this.socket.ev.on('groups.upsert', this.onGroupsUpsert);
    await this.socket.ev.on('group-participants.update', this.onGroupParticipantsUpdate);
    await this.socket.ev.on('creds.update', this.auth_state!.saveCreds);
  }

  static async cleanup(): Promise<void> {
    if (this.socket) {
      logger.info({ event: 'cleanup_started' });

      try {
        (this.socket.ev as unknown as { removeAllListeners(): void }).removeAllListeners();
        await this.socket.end(undefined);
      } catch (error) {
        Sentry.captureException(error);
        logger.error({ event: 'cleanup_failed', error: (error as Error).message });
      }
      this.socket = null;
      this.adapter = null;
    }
    CommandFactory.reset();
    this.bridge.disconnect();
    this.isConnecting = false;
  }
}
