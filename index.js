import Resenhazord2 from './src/models/Resenhazord2.js';
import dotenv from 'dotenv';

dotenv.config();

await Resenhazord2.connectToWhatsApp();
Resenhazord2.handlerEvents();
