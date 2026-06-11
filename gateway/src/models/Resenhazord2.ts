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
import GroupEventPublisher from '../bridge/GroupEventPublisher.js';
import CommandPublisher from '../bridge/CommandPublisher.js';
import BrokerForwarder from '../bridge/BrokerForwarder.js';
import ReplyConsumer from '../bridge/ReplyConsumer.js';
import WaActionConsumer from '../bridge/WaActionConsumer.js';
import WaRpcConsumer from '../bridge/WaRpcConsumer.js';
import InFlightCommands from '../bridge/InFlightCommands.js';
import MediaHandler from '../bridge/MediaHandler.js';
import RabbitBroker from '../infra/RabbitBroker.js';
import { Sentry } from '../infra/Sentry.js';
import logger from '../infra/Logger.js';

export default class Resenhazord2 {
  static auth_state: MongoDBAuthResult | null = null;
  private static socket: WASocket | null = null;
  static adapter: WhatsAppPort | null = null;
  static readonly broker = new RabbitBroker();
  static readonly groupEventPublisher = new GroupEventPublisher(this.broker);
  static readonly inFlightCommands = new InFlightCommands();
  static brokerForwarder: BrokerForwarder | null = null;
  static isConnecting = false;

  static async connectToWhatsApp(): Promise<void> {
    if (this.isConnecting) {
      logger.debug({ event: 'connection_already_in_progress' });
      return;
    }
    this.isConnecting = true;
    try {
      this.auth_state = await CreateAuthState.getAuthState();
      this.socket = await CreateSocket.getSocket(this.auth_state.state);
      this.adapter = new BaileysAdapter(this.socket);
      await this.connectBroker();
      logger.info({ event: 'socket_created' });
    } catch (error) {
      Sentry.captureException(error);
      logger.error({ event: 'connection_failed', error: (error as Error).message });
      throw error;
    } finally {
      this.isConnecting = false;
    }
  }

  private static async connectBroker(): Promise<void> {
    try {
      await this.broker.connect(process.env.RABBITMQ_URL ?? 'amqp://guest:guest@localhost:5672/');
      await this.startCommandPath();
    } catch (error) {
      logger.warn({ event: 'broker_unavailable', error: String(error) });
    }
  }

  private static async startCommandPath(): Promise<void> {
    const adapter = this.adapter!;
    const publisher = new CommandPublisher(this.broker, new MediaHandler(adapter));
    this.brokerForwarder = new BrokerForwarder(publisher, this.inFlightCommands);
    await new ReplyConsumer(this.broker, adapter, this.inFlightCommands).start();
    await new WaActionConsumer(this.broker, adapter).start();
    await new WaRpcConsumer(this.broker, adapter).start();
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
      logger.debug({ event: 'cleanup_started' });

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
    this.brokerForwarder = null;
    await this.broker.close();
    this.isConnecting = false;
  }
}
