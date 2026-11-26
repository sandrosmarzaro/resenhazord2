import logger from './Logger.js';
import { Sentry } from './Sentry.js';

type CloseReason = { code?: number | string; message?: string };

export function handleUnhandledRejection(reason: unknown): void {
  const error: CloseReason =
    reason && typeof reason === 'object' ? reason : { message: String(reason) };
  const code = typeof error.code !== 'undefined' ? error.code : error.message;
  if (String(code) === '1006') {
    logger.warn({ event: 'websocket_abnormal_closure', reason: error.message || String(reason) });
    return;
  }
  Sentry.captureException(reason);
}
