import { describe, it, expect, vi, beforeEach } from 'vitest';
import { handleUnhandledRejection } from '../../../src/infra/handleUnhandledRejection.js';

vi.mock('../../../src/infra/Logger.js', () => ({
  default: {
    warn: vi.fn(),
  },
}));

vi.mock('../../../src/infra/Sentry.js', () => ({
  Sentry: {
    captureException: vi.fn(),
  },
}));

import logger from '../../../src/infra/Logger.js';
import { Sentry } from '../../../src/infra/Sentry.js';

describe('handleUnhandledRejection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('warns and ignores when code is 1006', () => {
    handleUnhandledRejection({ code: 1006, message: 'abnormal closure' } as unknown as Error);
    expect(logger.warn).toHaveBeenCalledWith({
      event: 'websocket_abnormal_closure',
      reason: 'abnormal closure',
    });
    expect(Sentry.captureException).not.toHaveBeenCalled();
  });

  it('warns and ignores when message is 1006', () => {
    handleUnhandledRejection(new Error('1006'));
    expect(logger.warn).toHaveBeenCalledWith({
      event: 'websocket_abnormal_closure',
      reason: '1006',
    });
    expect(Sentry.captureException).not.toHaveBeenCalled();
  });

  it('warns and ignores when code is "1006"', () => {
    handleUnhandledRejection({ code: '1006', message: 'closed' } as unknown as Error);
    expect(logger.warn).toHaveBeenCalledWith({
      event: 'websocket_abnormal_closure',
      reason: 'closed',
    });
    expect(Sentry.captureException).not.toHaveBeenCalled();
  });

  it('sends other rejections to Sentry', () => {
    const error = new Error('boom');
    handleUnhandledRejection(error);
    expect(logger.warn).not.toHaveBeenCalled();
    expect(Sentry.captureException).toHaveBeenCalledWith(error);
  });

  it('sends undefined reason to Sentry without crashing', () => {
    handleUnhandledRejection(undefined);
    expect(logger.warn).not.toHaveBeenCalled();
    expect(Sentry.captureException).toHaveBeenCalledWith(undefined);
  });

  it('sends null reason to Sentry without crashing', () => {
    handleUnhandledRejection(null);
    expect(logger.warn).not.toHaveBeenCalled();
    expect(Sentry.captureException).toHaveBeenCalledWith(null);
  });
});
