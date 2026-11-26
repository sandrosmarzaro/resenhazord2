import { context, defaultTextMapSetter, trace, type Tracer } from '@opentelemetry/api';
import { W3CTraceContextPropagator } from '@opentelemetry/core';
import { OTLPMetricExporter } from '@opentelemetry/exporter-metrics-otlp-http';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { resourceFromAttributes } from '@opentelemetry/resources';
import { MeterProvider, PeriodicExportingMetricReader } from '@opentelemetry/sdk-metrics';
import { BasicTracerProvider, BatchSpanProcessor } from '@opentelemetry/sdk-trace-base';
import { ATTR_SERVICE_NAME } from '@opentelemetry/semantic-conventions';
import ProcessMemoryGauges from './ProcessMemoryGauges.js';

// Own provider + own propagator instances, never the global ones, so @sentry/bun's
// OpenTelemetry setup stays untouched. The edge node exports OTLP straight to Grafana
// Cloud (no collector there). Guarded on the endpoint like Sentry is on its DSN.
const propagator = new W3CTraceContextPropagator();
let tracer: Tracer | null = null;

function authHeaders(): Record<string, string> {
  // OTEL_EXPORTER_OTLP_HEADERS is `Authorization=Basic <base64>`; the value can hold
  // '=' padding, so split only on the first one.
  const raw = process.env.OTEL_EXPORTER_OTLP_HEADERS ?? '';
  const [key, ...rest] = raw.split('=');
  return key && rest.length ? { [key.trim()]: rest.join('=').trim() } : {};
}

export function initOtel(): void {
  const endpoint = process.env.OTEL_EXPORTER_OTLP_ENDPOINT;
  if (!endpoint) return;

  const headers = authHeaders();
  const resource = resourceFromAttributes({ [ATTR_SERVICE_NAME]: 'whatsapp' });
  const exporter = new OTLPTraceExporter({ url: `${endpoint}/v1/traces`, headers });
  const provider = new BasicTracerProvider({
    resource,
    spanProcessors: [new BatchSpanProcessor(exporter)],
  });
  tracer = provider.getTracer('gateway');

  const metricExporter = new OTLPMetricExporter({ url: `${endpoint}/v1/metrics`, headers });
  const meterProvider = new MeterProvider({
    resource,
    readers: [new PeriodicExportingMetricReader({ exporter: metricExporter })],
  });
  ProcessMemoryGauges.register(meterProvider.getMeter('gateway'));
}

// Start a publish span and write its W3C context into the envelope, so the core bot
// continues the same trace (it extracts `traceparent` on consume). No-op until initOtel
// runs — an explicit context is used instead of the active one, since Bun has no OTel
// context manager registered.
export function injectPublishTrace(carrier: Record<string, unknown>): void {
  if (!tracer) return;
  const span = tracer.startSpan('gateway.publish');
  const ctx = trace.setSpan(context.active(), span);
  propagator.inject(ctx, carrier, defaultTextMapSetter);
  span.end();
}
