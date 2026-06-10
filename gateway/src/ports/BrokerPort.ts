export type MessageHandler = (body: Buffer) => Promise<void>;

export default interface BrokerPort {
  connect(url: string): Promise<void>;
  publish(queue: string, body: Buffer): Promise<void>;
  consume(queue: string, handler: MessageHandler): Promise<void>;
  close(): Promise<void>;
}
