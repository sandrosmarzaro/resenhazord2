import { isBoom } from '@hapi/boom';
import { DisconnectReason } from '@whiskeysockets/baileys';
import type { BaileysEventMap } from '@whiskeysockets/baileys';
import Resenhazord2 from '../models/Resenhazord2.js';
import { Sentry } from '../infra/Sentry.js';

const DISCONNECT_REASON_METHOD_NOT_ALLOWED = 405;

export default class ConnectionUpdateEvent {
  static reconnectAttempts = 0;
  static maxReconnectAttempts = 5;
  static isReconnecting = false;
  static reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  static async run(update: BaileysEventMap['connection.update']): Promise<void> {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      console.log(`QR Code received: ${qr}`);
    }

    if (connection === 'close') {
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }

      const error = lastDisconnect?.error;
      const statusCode = error && isBoom(error) ? error.output?.statusCode : null;

      console.log(`Connection closed. Status code: ${statusCode || 'unknown'}`);
      console.log(`Error: ${error?.message || 'Unknown error'}`);
      console.log(`Reconnect attempts so far: ${this.reconnectAttempts}`);

      if (statusCode === DisconnectReason.loggedOut) {
        console.log('❌ Logged out. Please scan QR code again.');
        Sentry.captureMessage('Bot logged out', 'warning');
        this.reset();
        return;
      }

      if (statusCode === DisconnectReason.badSession) {
        console.log('❌ Bad session. Delete auth_session folder and restart.');
        this.reset();
        return;
      }

      const shouldReconnect =
        !statusCode ||
        statusCode === DISCONNECT_REASON_METHOD_NOT_ALLOWED ||
        [
          DisconnectReason.connectionClosed,
          DisconnectReason.connectionLost,
          DisconnectReason.connectionReplaced,
          DisconnectReason.timedOut,
          DisconnectReason.restartRequired,
          DisconnectReason.unavailableService,
        ].includes(statusCode);

      if (shouldReconnect) {
        await this.scheduleReconnect();
      } else {
        console.log(`⚠️  Not reconnecting for status code: ${statusCode}`);
        this.reset();
      }
    } else if (connection === 'connecting') {
      console.log('🔄 Connecting to WhatsApp...');
    } else if (connection === 'open') {
      console.log('✅ Connection opened successfully');
      Sentry.addBreadcrumb({
        category: 'whatsapp.connection',
        message: `Status: ${connection}`,
        level: 'info',
      });
      this.reset();
    }
  }

  static async scheduleReconnect(): Promise<void> {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log(`❌ Max reconnection attempts (${this.maxReconnectAttempts}) reached. Stopping.`);
      Sentry.captureMessage(
        `Max reconnection attempts (${this.maxReconnectAttempts}) reached`,
        'fatal',
      );
      this.reset();
      return;
    }

    this.reconnectAttempts++;

    const delay = Math.min(3000 * Math.pow(2, this.reconnectAttempts - 1), 48000);

    console.log(
      `🔄 Reconnecting in ${delay / 1000}s... (Attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`,
    );

    this.reconnectTimer = setTimeout(async () => {
      if (this.isReconnecting) {
        console.log('⚠️  Previous reconnection still in progress');
        return;
      }

      this.isReconnecting = true;

      try {
        console.log('🔌 Attempting to reconnect...');

        await Resenhazord2.cleanup?.();

        await Resenhazord2.connectToWhatsApp();
        await Resenhazord2.handlerEvents();
      } catch (error) {
        Sentry.captureException(error, { extra: { attempt: this.reconnectAttempts } });
        console.error('❌ Reconnection failed:', (error as Error).message);
        this.isReconnecting = false;

        await this.scheduleReconnect();
      } finally {
        this.isReconnecting = false;
      }
    }, delay);
  }

  static reset(): void {
    this.reconnectAttempts = 0;
    this.isReconnecting = false;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}
