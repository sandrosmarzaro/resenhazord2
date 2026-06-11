import type { MiscMessageGenerationOptions, WAMessage } from '@whiskeysockets/baileys';
import type BrokerPort from '../ports/BrokerPort.js';
import type WhatsAppPort from '../ports/WhatsAppPort.js';
import type InFlightCommands from './InFlightCommands.js';
import ReplyDeserializer from './ReplyDeserializer.js';
import TypingIndicator from '../utils/TypingIndicator.js';
import logger from '../infra/Logger.js';

interface ReplyEnvelope {
  id: string;
  messages: Record<string, unknown>[];
}

export default class ReplyConsumer {
  private static readonly QUEUE = 'replies';

  constructor(
    private readonly broker: BrokerPort,
    private readonly whatsapp: WhatsAppPort,
    private readonly inFlight: InFlightCommands,
  ) {}

  async start(): Promise<void> {
    await this.broker.consume(ReplyConsumer.QUEUE, (body) => this.handle(body));
  }

  private async handle(body: Buffer): Promise<void> {
    const envelope = JSON.parse(body.toString()) as ReplyEnvelope;
    // Carry the correlation id in the gateway's logs too, so one id spans both
    // processes when tracing a command (§12).
    logger.info({ event: 'reply_received', correlationId: envelope.id });

    // The registry carries the jid even for an empty terminal reply (no-output
    // commands), so the typing indicator always stops. It also holds the original
    // message, which Baileys needs to quote the reply.
    const command = this.inFlight.resolve(envelope.id);
    for (const raw of envelope.messages) {
      const message = await ReplyDeserializer.toMessage(raw);
      const options = ReplyConsumer.withQuoted(message.options, raw, command?.quoted);
      await this.whatsapp.sendMessage(message.jid, message.content, options);
    }

    if (command) await TypingIndicator.stop(command.jid);
  }

  private static withQuoted(
    options: MiscMessageGenerationOptions | undefined,
    raw: Record<string, unknown>,
    quoted: WAMessage | undefined,
  ): MiscMessageGenerationOptions {
    if (raw.quoted_message_id && quoted) return { ...options, quoted };
    return options ?? {};
  }
}
