export interface BrokerBinding {
  exchange: string;
  pattern: string;
  queue: string;
}

export interface BrokerTopology {
  exchanges: string[];
  queues: Record<string, Record<string, number | string>>;
  bindings: BrokerBinding[];
}
