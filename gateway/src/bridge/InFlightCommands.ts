export default class InFlightCommands {
  private readonly byId = new Map<string, string>();

  track(id: string, jid: string): void {
    this.byId.set(id, jid);
  }

  resolve(id: string): string | undefined {
    const jid = this.byId.get(id);
    this.byId.delete(id);
    return jid;
  }
}
