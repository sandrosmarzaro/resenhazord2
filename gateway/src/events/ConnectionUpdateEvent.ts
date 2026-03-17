import { isBoom } from '@hapi/boom';
import { DisconnectReason } from '@whiskeysockets/baileys';
import type { BaileysEventMap } from '@whiskeysockets/baileys';
import Resenhazord2 from '../models/Resenhazord2.js';
import { Sentry } from '../infra/Sentry.js';

export default class ConnectionUpdateEvent {
  private static readonly DISCONNECT_REASON_METHOD_NOT_ALLOWED = 405;
  private static readonly RECONNECTABLE_REASONS = new Set([
    DisconnectReason.connectionClosed,
    DisconnectReason.connectionLost,
    DisconnectReason.connectionReplaced,
    DisconnectReason.timedOut,
    DisconnectReason.restartRequired,
    DisconnectReason.unavailableService,
  ]);

  static reconnectAttempts = 0;
  static maxReconnectAttempts = 5;
  static isReconnecting = false;
  static reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  static async run(update: BaileysEventMap['connection.update']): Promise<void> {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      Sentry.logger.info(Sentry.logger.fmt`QR Code received: ${qr}`);
    }

    if (connection === 'close') {
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }

      const error = lastDisconnect?.error;
      const statusCode = error && isBoom(error) ? error.output?.statusCode : null;

      Sentry.addBreadcrumb({
        category: 'whatsapp.connection',
        message: `Connection closed. Status: ${statusCode ?? 'unknown'}`,
        level: 'warning',
        data: { statusCode, error: error?.message },
      });
      Sentry.logger.warn(
        Sentry.logger.fmt`Connection closed. Status code: ${statusCode ?? 'unknown'}`,
      );
      Sentry.logger.warn(Sentry.logger.fmt`Error: ${error?.message ?? 'Unknown error'}`);
      Sentry.logger.info(Sentry.logger.fmt`Reconnect attempts so far: ${this.reconnectAttempts}`);

      if (statusCode === DisconnectReason.loggedOut) {
        Sentry.logger.warn('Logged out. Please scan QR code again.');
        Sentry.captureMessage('Bot logged out', 'warning');
        this.reset();
        return;
      }

      if (statusCode === DisconnectReason.badSession) {
        Sentry.logger.warn('Bad session. Delete auth_session folder and restart.');
        this.reset();
        return;
      }

      const shouldReconnect =
        !statusCode ||
        statusCode === ConnectionUpdateEvent.DISCONNECT_REASON_METHOD_NOT_ALLOWED ||
        ConnectionUpdateEvent.RECONNECTABLE_REASONS.has(statusCode);

      if (shouldReconnect) {
        await this.scheduleReconnect();
      } else {
        Sentry.logger.warn(Sentry.logger.fmt`Not reconnecting for status code: ${statusCode}`);
        this.reset();
      }
    } else if (connection === 'connecting') {
      Sentry.logger.info('Connecting to WhatsApp...');
    } else if (connection === 'open') {
      Sentry.logger.info('Connection opened successfully');
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
      Sentry.logger.error(
        Sentry.logger
          .fmt`Max reconnection attempts (${this.maxReconnectAttempts}) reached. Stopping.`,
      );
      Sentry.captureMessage(
        `Max reconnection attempts (${this.maxReconnectAttempts}) reached`,
        'fatal',
      );
      this.reset();
      return;
    }

    this.reconnectAttempts++;

    const delay = Math.min(3000 * 2 ** (this.reconnectAttempts - 1), 48000);

    Sentry.logger.info(
      Sentry.logger
        .fmt`Reconnecting in ${delay / 1000}s... (Attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`,
    );

    this.reconnectTimer = setTimeout(async () => {
      if (this.isReconnecting) {
        Sentry.logger.warn('Previous reconnection still in progress');
        return;
      }

      this.isReconnecting = true;

      try {
        Sentry.logger.info('Attempting to reconnect...');

        await Resenhazord2.cleanup?.();

        await Resenhazord2.connectToWhatsApp();
        await Resenhazord2.handlerEvents();
      } catch (error) {
        Sentry.captureException(error, { extra: { attempt: this.reconnectAttempts } });
        Sentry.logger.error(Sentry.logger.fmt`Reconnection failed: ${(error as Error).message}`);

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
