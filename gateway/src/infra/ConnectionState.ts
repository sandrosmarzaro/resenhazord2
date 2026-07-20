import { unlink, writeFile } from 'node:fs/promises';

// `pidof bun` proves nothing: a logged-out gateway keeps its process alive and mute.
// The marker file exists only while Baileys reports an open connection, so the
// container healthcheck can tell "running" apart from "actually connected".
export default class ConnectionState {
  // Home, not /tmp: the marker gates the healthcheck, so it must live somewhere
  // only this container's user can write to.
  static readonly MARKER_PATH = `${process.env.HOME}/.whatsapp-connected`;

  static async markOpen(): Promise<void> {
    await writeFile(ConnectionState.MARKER_PATH, String(Date.now()));
  }

  static async markClosed(): Promise<void> {
    await unlink(ConnectionState.MARKER_PATH).catch(() => {});
  }
}
