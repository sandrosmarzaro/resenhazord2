import { isBoom } from '@hapi/boom';
import { DisconnectReason } from '@whiskeysockets/baileys';
import type { BaileysEventMap } from '@whiskeysockets/baileys';
import Resenhazord2 from '../models/Resenhazord2.js';
import { Sentry } from '../infra/Sentry.js';
import logger from '../infra/Logger.js';

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
      logger.info({ event: 'qr_received', qr });
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
      logger.warn({
        event: 'connection_closed',
        statusCode: statusCode ?? 'unknown',
        error: error?.message ?? 'Unknown error',
        reconnectAttempts: this.reconnectAttempts,
      });

      if (statusCode === DisconnectReason.loggedOut) {
        logger.warn({ event: 'logged_out' });
        Sentry.captureMessage('Bot logged out', 'warning');
        this.reset();
        return;
      }

      if (statusCode === DisconnectReason.badSession) {
        logger.warn({ event: 'bad_session' });
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
        logger.warn({ event: 'reconnect_skipped', statusCode });
        this.reset();
      }
    } else if (connection === 'connecting') {
      logger.debug({ event: 'connecting' });
    } else if (connection === 'open') {
      logger.info({ event: 'connection_opened' });
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
      logger.error({ event: 'max_reconnect_attempts_reached', max: this.maxReconnectAttempts });
      Sentry.captureMessage(
        `Max reconnection attempts (${this.maxReconnectAttempts}) reached`,
        'fatal',
      );
      this.reset();
      return;
    }

    this.reconnectAttempts++;

    const delay = Math.min(3000 * 2 ** (this.reconnectAttempts - 1), 48000);

    logger.info({
      event: 'reconnect_scheduled',
      delaySeconds: delay / 1000,
      attempt: this.reconnectAttempts,
      maxAttempts: this.maxReconnectAttempts,
    });

    this.reconnectTimer = setTimeout(async () => {
      if (this.isReconnecting) {
        logger.warn({ event: 'reconnect_already_in_progress' });
        return;
      }

      this.isReconnecting = true;

      try {
        logger.info({ event: 'reconnecting' });

        await Resenhazord2.cleanup?.();

        await Resenhazord2.connectToWhatsApp();
        await Resenhazord2.handlerEvents();
      } catch (error) {
        Sentry.captureException(error, { extra: { attempt: this.reconnectAttempts } });
        logger.error({ event: 'reconnect_failed', error: (error as Error).message });

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
