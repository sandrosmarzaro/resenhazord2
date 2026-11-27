export interface BrokerBinding {
  exchange: string;
  pattern: string;
  queue: string;
}

export interface BrokerTopology {
  exchanges: string[];
  // A headers exchange that routes a dead letter by its x-last-death-reason (ADR 0004).
  deadLetterExchange: string;
  queues: Record<string, Record<string, number | string>>;
  bindings: BrokerBinding[];
  // Death reason → the queue it goes to. A reason without a route is dropped.
  deadLetterRoutes: Record<string, string>;
}
