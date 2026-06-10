import type BrokerPort from '../ports/BrokerPort.js';
import type WhatsAppPort from '../ports/WhatsAppPort.js';
import ReplyDeserializer from './ReplyDeserializer.js';

interface ReplyEnvelope {
  id: string;
  messages: Record<string, unknown>[];
}

export default class ReplyConsumer {
  private static readonly QUEUE = 'replies';

  constructor(
    private readonly broker: BrokerPort,
    private readonly whatsapp: WhatsAppPort,
  ) {}

  async start(): Promise<void> {
    await this.broker.consume(ReplyConsumer.QUEUE, (body) => this.handle(body));
  }

  private async handle(body: Buffer): Promise<void> {
    const envelope = JSON.parse(body.toString()) as ReplyEnvelope;
    for (const raw of envelope.messages) {
      const message = await ReplyDeserializer.toMessage(raw);
      await this.whatsapp.sendMessage(message.jid, message.content, message.options ?? {});
    }
  }
}
