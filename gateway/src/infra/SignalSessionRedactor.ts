// libsignal (Baileys' Signal implementation) prints whole SessionEntry objects through
// console on session open/close, and those carry the ratchet and root private keys into
// the container logs. Keep the message, which is a useful re-key signal; drop the keys.
export default class SignalSessionRedactor {
  private static readonly METHODS = ['log', 'info', 'warn', 'error', 'debug'] as const;
  private static readonly PLACEHOLDER = '[SessionEntry redacted]';

  static install(target: Console = console): void {
    for (const method of SignalSessionRedactor.METHODS) {
      const print = target[method].bind(target);
      target[method] = (...args: unknown[]) => print(...args.map(SignalSessionRedactor.redact));
    }
  }

  private static redact(this: void, arg: unknown): unknown {
    return arg?.constructor?.name === 'SessionEntry' ? SignalSessionRedactor.PLACEHOLDER : arg;
  }
}
