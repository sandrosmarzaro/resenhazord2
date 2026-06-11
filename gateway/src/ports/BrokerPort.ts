export type MessageHandler = (body: Buffer) => Promise<void>;
export type RpcHandler = (body: Buffer) => Promise<Buffer>;

export default interface BrokerPort {
  connect(url: string): Promise<void>;
  publish(queue: string, body: Buffer): Promise<void>;
  consume(queue: string, handler: MessageHandler): Promise<void>;
  respondRpc(queue: string, handler: RpcHandler): Promise<void>;
  close(): Promise<void>;
}
