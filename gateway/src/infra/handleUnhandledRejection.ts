import logger from './Logger.js';
import { Sentry } from './Sentry.js';

export function handleUnhandledRejection(reason: unknown): void {
  if (!reason || typeof reason !== 'object') {
    Sentry.captureException(reason);
    return;
  }
  const error = reason as Error & { code?: number | string };
  const code = typeof error.code !== 'undefined' ? error.code : error.message;
  if (code === 1006 || code === '1006') {
    logger.warn({ event: 'websocket_abnormal_closure', reason: error.message || String(reason) });
    return;
  }
  Sentry.captureException(reason);
}
