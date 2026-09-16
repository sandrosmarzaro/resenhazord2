import { describe, it, expect } from 'vitest';

import { initOtel, injectPublishTrace } from '../../../src/infra/Otel.js';

describe('Otel', () => {
  it('injectPublishTrace is a no-op before init', () => {
    const carrier: Record<string, unknown> = {};

    injectPublishTrace(carrier);

    expect(carrier).toEqual({});
  });

  it('initOtel is a no-op without an OTLP endpoint', () => {
    delete process.env.OTEL_EXPORTER_OTLP_ENDPOINT;

    expect(() => initOtel()).not.toThrow();

    const carrier: Record<string, unknown> = {};
    injectPublishTrace(carrier);
    expect(carrier).toEqual({});
  });
});
