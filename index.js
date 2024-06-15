import Resenhazord2 from './src/models/Resenhazord2.js';
import dotenv from 'dotenv';
import Bugsnag from '@bugsnag/js';

dotenv.config();
Resenhazord2.bugsnag = Bugsnag.start({
    apiKey: process.env.BUGSNAG_API_KEY,
    appType: 'websocket_server',
});
await Resenhazord2.connectToWhatsApp();
Resenhazord2.handlerEvents();
