import type { Meter } from '@opentelemetry/api';

// The edge VM swap-thrashes every few days and the gateway is the only process on it that
// grows (#393). RSS says how big it is; heap against external says whether JS objects or
// Buffers (media downloads) hold the memory. RSS matches the core bot's metric name.
export default class ProcessMemoryGauges {
  static register(meter: Meter): void {
    const rss = meter.createObservableGauge('process.memory.rss', {
      unit: 'By',
      description: 'Resident memory of the gateway process',
    });
    const heapUsed = meter.createObservableGauge('process.memory.heap_used', {
      unit: 'By',
      description: 'JavaScript heap in use',
    });
    const external = meter.createObservableGauge('process.memory.external', {
      unit: 'By',
      description: 'Memory held outside the JavaScript heap, Buffers included',
    });
    meter.addBatchObservableCallback(
      (result) => {
        const usage = process.memoryUsage();
        result.observe(rss, usage.rss);
        result.observe(heapUsed, usage.heapUsed);
        result.observe(external, usage.external);
      },
      [rss, heapUsed, external],
    );
  }
}
