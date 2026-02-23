import Resenhazord2 from '../models/Resenhazord2.js';

export default class ReactMessage {
  static async run(data) {
    await Resenhazord2.socket.sendMessage(data.key.remoteJid, {
      react: {
        text: '👍',
        key: data.key,
      },
    });
  }
}
