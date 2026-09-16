import { Sentry } from './src/infra/Sentry.js';
import Resenhazord2 from './src/models/Resenhazord2.js';
import MongoDBConnection from './src/infra/MongoDBConnection.js';
import logger from './src/infra/Logger.js';
import { handleUnhandledRejection } from './src/infra/handleUnhandledRejection.js';
import { initOtel } from './src/infra/Otel.js';
import dotenv from 'dotenv';

dotenv.config();
// After dotenv so the OTLP endpoint/headers resolve from .env in local dev.
initOtel();

process.on('uncaughtException', (err) => {
  Sentry.captureException(err);
  process.exit(1);
});

process.on('unhandledRejection', handleUnhandledRejection);

const shutdown = async () => {
  logger.info({ event: 'shutdown' });
  await Resenhazord2.cleanup();
  await MongoDBConnection.close();
  process.exit(0);
};

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);

await Resenhazord2.connectToWhatsApp();
Resenhazord2.handlerEvents();
