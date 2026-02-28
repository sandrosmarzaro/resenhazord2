import type { WASocket, BaileysEventMap } from '@whiskeysockets/baileys';
import type { MongoDBAuthResult } from '../auth/MongoDBAuthState.js';
import CreateSocket from '../infra/CreateSocket.js';
import CreateAuthState from '../auth/CreateAuthState.js';
import MessageUpsertEvent from '../events/MessageUpsertEvent.js';
import ConnectionUpdateEvent from '../events/ConnectionUpdateEvent.js';
import GroupParticipantsUpdateEvent from '../events/GroupParticipantsUpdateEvent.js';
import groupMetadataCache from '../utils/GroupMetadataCache.js';
import MongoDBConnection from '../infra/MongoDBConnection.js';

export default class Resenhazord2 {
  static auth_state: MongoDBAuthResult | null = null;
  static socket: WASocket | null = null;
  static isConnecting = false;

  static async connectToWhatsApp(): Promise<void> {
    if (this.isConnecting) {
      console.log('Connection already in progress...');
      return;
    }
    this.isConnecting = true;
    try {
      this.auth_state = await CreateAuthState.getAuthState();
      this.socket = await CreateSocket.getSocket(this.auth_state.state);
      console.log('Socket created successfully');
    } catch (error) {
      console.error('Failed to connect:', (error as Error).message);
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

  static onGroupsUpsert(groups: BaileysEventMap['groups.upsert']): void {
    for (const group of groups) {
      groupMetadataCache.set(group.id, group);
    }
  }

  static async onGroupParticipantsUpdate(
    data: BaileysEventMap['group-participants.update'],
  ): Promise<void> {
    try {
      const meta = await Resenhazord2.socket!.groupMetadata(data.id);
      groupMetadataCache.set(data.id, meta);
    } catch {
      // ignore
    }
    await GroupParticipantsUpdateEvent.run(data);
  }

  static async handlerEvents(): Promise<void> {
    if (!this.socket) {
      console.error('Cannot setup handlers: socket is null');
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
      console.log('Cleaning up existing socket...');

      try {
        (this.socket.ev as unknown as { removeAllListeners(): void }).removeAllListeners();
        await this.socket.end(undefined);
      } catch (error) {
        console.error('Error during cleanup:', (error as Error).message);
      }
      this.socket = null;
    }
    this.isConnecting = false;

    if (MongoDBConnection.isConnected()) {
      console.log('Closing MongoDB connection...');
      await MongoDBConnection.close();
    }
  }
}
