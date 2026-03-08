import { Sentry } from './src/infra/Sentry.js';
import Resenhazord2 from './src/models/Resenhazord2.js';
import dotenv from 'dotenv';

dotenv.config();

process.on('uncaughtException', (err) => {
  Sentry.captureException(err);
  process.exit(1);
});

process.on('unhandledRejection', (reason) => {
  Sentry.captureException(reason);
});

const shutdown = async () => {
  console.log('Shutting down...');
  await Resenhazord2.cleanup();
  process.exit(0);
};

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);

await Resenhazord2.connectToWhatsApp();
Resenhazord2.handlerEvents();
