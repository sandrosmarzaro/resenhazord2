import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { Sentry } from '../../../src/infra/Sentry.js';

describe('ConnectionWatchdog', () => {
  let ConnectionWatchdog: typeof import('../../../src/infra/ConnectionWatchdog.js').default;
  let exitSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(async () => {
    vi.useFakeTimers();
    vi.resetModules();
    exitSpy = vi.spyOn(process, 'exit').mockImplementation(() => undefined as never);
    ({ default: ConnectionWatchdog } = await import('../../../src/infra/ConnectionWatchdog.js'));
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  describe('arm', () => {
    it('exits with status 1 when the connection never opens before the timeout', () => {
      ConnectionWatchdog.arm();

      vi.advanceTimersByTime(120_000);

      expect(exitSpy).toHaveBeenCalledWith(1);
    });

    it('reports the expiry to Sentry as fatal before exiting', () => {
      ConnectionWatchdog.arm();

      vi.advanceTimersByTime(120_000);

      expect(Sentry.captureMessage).toHaveBeenCalledWith(expect.any(String), 'fatal');
    });

    it('re-arming restarts the countdown instead of stacking timers', () => {
      ConnectionWatchdog.arm();
      vi.advanceTimersByTime(119_000);
      ConnectionWatchdog.arm();
      vi.advanceTimersByTime(119_000);

      expect(exitSpy).not.toHaveBeenCalled();
    });
  });

  describe('disarm', () => {
    it('does not exit when the connection opens before the timeout', () => {
      ConnectionWatchdog.arm();
      ConnectionWatchdog.disarm();

      vi.advanceTimersByTime(120_000);

      expect(exitSpy).not.toHaveBeenCalled();
    });
  });

  describe('disable', () => {
    it('ignores a later arm so a terminal session does not crash-loop the container', () => {
      ConnectionWatchdog.disable();
      ConnectionWatchdog.arm();

      vi.advanceTimersByTime(120_000);

      expect(exitSpy).not.toHaveBeenCalled();
    });
  });
});
