import type BrokerPort from '../ports/BrokerPort.js';
import type WhatsAppPort from '../ports/WhatsAppPort.js';

interface RpcRequest {
  method: string;
  jids?: string[];
  jid?: string;
}

export default class WaRpcConsumer {
  private static readonly QUEUE = 'wa_rpc';

  constructor(
    private readonly broker: BrokerPort,
    private readonly whatsapp: WhatsAppPort,
  ) {}

  async start(): Promise<void> {
    await this.broker.respondRpc(WaRpcConsumer.QUEUE, (body) => this.handle(body));
  }

  private async handle(body: Buffer): Promise<Buffer> {
    const request = JSON.parse(body.toString()) as RpcRequest;
    const result = await this.dispatch(request);
    return Buffer.from(JSON.stringify(result));
  }

  private async dispatch(request: RpcRequest): Promise<unknown> {
    if (request.method === 'on_whatsapp') {
      return { results: await this.whatsapp.onWhatsApp(...(request.jids ?? [])) };
    }
    if (request.method === 'group_metadata') {
      return this.whatsapp.groupMetadata(request.jid ?? '');
    }
    throw new Error(`Unknown wa_rpc method: ${request.method}`);
  }
}
