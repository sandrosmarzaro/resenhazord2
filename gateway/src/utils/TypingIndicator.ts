import Resenhazord2 from '../models/Resenhazord2.js';

export default class TypingIndicator {
  static async start(jid: string): Promise<void> {
    try {
      await Resenhazord2.adapter!.sendPresenceUpdate('composing', jid);
    } catch {
      // best-effort — never block command execution
    }
  }

  static async stop(jid: string): Promise<void> {
    try {
      await Resenhazord2.adapter!.sendPresenceUpdate('paused', jid);
    } catch {
      // best-effort — never block command execution
    }
  }
}
