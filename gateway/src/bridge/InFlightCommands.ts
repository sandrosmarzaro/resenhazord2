import type { WAMessage } from '@whiskeysockets/baileys';

export interface InFlightCommand {
  jid: string;
  quoted: WAMessage;
}

// A command the bot never answers (dropped from the full `commands` queue, an envelope it
// could not parse) would stay here for the life of the process. The queue holds 100 and
// the DLQ 500, so past this many the oldest can no longer be answered and is dropped.
export default class InFlightCommands {
  private static readonly CAPACITY = 1000;
  private readonly byId = new Map<string, InFlightCommand>();

  constructor(private readonly capacity = InFlightCommands.CAPACITY) {}

  track(id: string, jid: string, quoted: WAMessage): void {
    this.byId.set(id, { jid, quoted });
    if (this.byId.size <= this.capacity) return;
    // A Map iterates in insertion order, so the first key is the oldest command.
    const [oldest] = this.byId.keys();
    this.byId.delete(oldest);
  }

  resolve(id: string): InFlightCommand | undefined {
    const command = this.byId.get(id);
    this.byId.delete(id);
    return command;
  }
}
