import { Sentry } from './Sentry.js';
import logger from './Logger.js';

// The container's healthcheck only proves `bun` is running, and Docker's restart
// policy never reacts to health status. A gateway that creates its socket but never
// reaches `connection_opened` (or exhausts its reconnect budget) stays alive yet mute.
// This watchdog turns that silent stall into a non-zero exit so `restart: unless-stopped`
// brings the gateway back from scratch.
export default class ConnectionWatchdog {
  private static readonly TIMEOUT_MS = 120_000;
  private static timer: ReturnType<typeof setTimeout> | null = null;
  private static disabled = false;

  static arm(): void {
    if (this.disabled) {
      return;
    }
    this.clearTimer();
    this.timer = setTimeout(() => this.expire(), this.TIMEOUT_MS);
  }

  static disarm(): void {
    this.clearTimer();
  }

  // Terminal states (logged out, bad session) need a human to re-pair: restarting would
  // only reload the same dead credentials, so silence the watchdog until the next boot.
  static disable(): void {
    this.disabled = true;
    this.clearTimer();
  }

  private static clearTimer(): void {
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  }

  private static expire(): void {
    logger.error({
      event: 'connection_watchdog_expired',
      timeoutSeconds: this.TIMEOUT_MS / 1000,
    });
    Sentry.captureMessage('WhatsApp connection watchdog expired; exiting for restart', 'fatal');
    process.exit(1);
  }
}
