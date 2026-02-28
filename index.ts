import Resenhazord2 from './src/models/Resenhazord2.js';
import dotenv from 'dotenv';

dotenv.config();

const shutdown = async () => {
  console.log('Shutting down...');
  await Resenhazord2.cleanup();
  process.exit(0);
};

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);

await Resenhazord2.connectToWhatsApp();
Resenhazord2.handlerEvents();
