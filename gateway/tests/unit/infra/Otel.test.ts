import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('Otel', () => {
  beforeEach(() => {
    vi.resetModules();
    delete process.env.OTEL_EXPORTER_OTLP_ENDPOINT;
    delete process.env.OTEL_EXPORTER_OTLP_HEADERS;
  });

  it('injectPublishTrace is a no-op before init', async () => {
    const { injectPublishTrace } = await import('../../../src/infra/Otel.js');
    const carrier: Record<string, unknown> = {};

    injectPublishTrace(carrier);

    expect(carrier).toEqual({});
  });

  it('initOtel is a no-op without an OTLP endpoint', async () => {
    const { initOtel, injectPublishTrace } = await import('../../../src/infra/Otel.js');

    expect(() => initOtel()).not.toThrow();

    const carrier: Record<string, unknown> = {};
    injectPublishTrace(carrier);
    expect(carrier).toEqual({});
  });

  it('injects a W3C traceparent into the envelope once initialised', async () => {
    process.env.OTEL_EXPORTER_OTLP_ENDPOINT = 'http://localhost:4318';
    process.env.OTEL_EXPORTER_OTLP_HEADERS = 'Authorization=Basic dXNlcjpwYXNz';
    const { initOtel, injectPublishTrace } = await import('../../../src/infra/Otel.js');
    initOtel();

    const carrier: Record<string, unknown> = {};
    injectPublishTrace(carrier);

    expect(carrier.traceparent).toMatch(/^00-[0-9a-f]{32}-[0-9a-f]{16}-01$/);
  });

  it('initialises with no auth headers when OTEL_EXPORTER_OTLP_HEADERS is unset', async () => {
    process.env.OTEL_EXPORTER_OTLP_ENDPOINT = 'http://localhost:4318';
    const { initOtel, injectPublishTrace } = await import('../../../src/infra/Otel.js');
    initOtel();

    const carrier: Record<string, unknown> = {};
    injectPublishTrace(carrier);

    expect(carrier.traceparent).toMatch(/^00-[0-9a-f]{32}-[0-9a-f]{16}-01$/);
  });
});
