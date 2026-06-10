import type { WAMessage } from '@whiskeysockets/baileys';
import type { CommandData } from '../types/command.js';
import type CommandPublisher from './CommandPublisher.js';
import type InFlightCommands from './InFlightCommands.js';
import GetGroupExpiration from '../utils/GetGroupExpiration.js';
import ReactMessage from '../utils/ReactMessage.js';
import TypingIndicator from '../utils/TypingIndicator.js';
import { Sentry } from '../infra/Sentry.js';
import logger from '../infra/Logger.js';

export default class BrokerForwarder {
  constructor(
    private readonly publisher: CommandPublisher,
    private readonly inFlight: InFlightCommands,
  ) {}

  async forward(data: WAMessage, text: string): Promise<void> {
    const commandData = await BrokerForwarder.buildCommandData(data, text);
    const jid = commandData.key.remoteJid;
    if (!jid) return;

    // Drive feedback locally and immediately on the parser match — no command_ack
    // round-trip. ReplyConsumer stops the indicator when the reply lands.
    await ReactMessage.run(data);
    await TypingIndicator.start(jid);

    try {
      const id = await this.publisher.publish(commandData);
      this.inFlight.track(id, jid);
    } catch (error) {
      logger.error({ event: 'command_publish_failed', jid, error: String(error) });
      Sentry.captureException(error);
      await TypingIndicator.stop(jid);
    }
  }

  private static async buildCommandData(data: WAMessage, text: string): Promise<CommandData> {
    return {
      ...data,
      text,
      expiration: await GetGroupExpiration.run(data),
    } as CommandData;
  }
}
