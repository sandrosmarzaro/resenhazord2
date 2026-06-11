import type { WAMessage } from '@whiskeysockets/baileys';

export interface InFlightCommand {
  jid: string;
  quoted: WAMessage;
}

export default class InFlightCommands {
  private readonly byId = new Map<string, InFlightCommand>();

  track(id: string, jid: string, quoted: WAMessage): void {
    this.byId.set(id, { jid, quoted });
  }

  resolve(id: string): InFlightCommand | undefined {
    const command = this.byId.get(id);
    this.byId.delete(id);
    return command;
  }
}
