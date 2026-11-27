import { describe, it, expect } from 'vitest';
import { MeterProvider, MetricReader } from '@opentelemetry/sdk-metrics';
import ProcessMemoryGauges from '../../../src/infra/ProcessMemoryGauges.js';

class CollectingReader extends MetricReader {
  protected async onForceFlush(): Promise<void> {}
  protected async onShutdown(): Promise<void> {}
}

async function collectGauges(): Promise<Record<string, number>> {
  const reader = new CollectingReader();
  const provider = new MeterProvider({ readers: [reader] });
  ProcessMemoryGauges.register(provider.getMeter('test'));

  const { resourceMetrics } = await reader.collect();

  const metrics = resourceMetrics.scopeMetrics.flatMap((scope) => scope.metrics);
  return Object.fromEntries(
    metrics.map((metric) => [metric.descriptor.name, Number(metric.dataPoints[0].value)]),
  );
}

describe('ProcessMemoryGauges', () => {
  it('reports resident memory, JS heap and external memory in bytes', async () => {
    const gauges = await collectGauges();

    expect(Object.keys(gauges).sort()).toEqual([
      'process.memory.external',
      'process.memory.heap_used',
      'process.memory.rss',
    ]);
    expect(Object.values(gauges).every((bytes) => bytes > 0)).toBe(true);
  });
});
