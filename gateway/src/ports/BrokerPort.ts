export default interface BrokerPort {
  connect(url: string): Promise<void>;
  publish(queue: string, body: Buffer): Promise<void>;
  close(): Promise<void>;
}
