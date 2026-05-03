import type { WAMessage } from '@whiskeysockets/baileys';
import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Resenhazord2 from '../models/Resenhazord2.js';
import GetGroupExpiration from '../utils/GetGroupExpiration.js';
import ReactMessage from '../utils/ReactMessage.js';
import TypingIndicator from '../utils/TypingIndicator.js';
import { Sentry } from '../infra/Sentry.js';
import logger from '../infra/Logger.js';

export default class PythonForwarder {
  private static readonly ERROR_TEXT = 'Ocorreu um erro ao processar o comando 😔';
  private static readonly TEXT_PREVIEW_LENGTH = 200;

  static async forward(
    data: WAMessage,
    text: string,
    sendBatch: (messages: Message[]) => Promise<void>,
  ): Promise<void> {
    logger.info({ event: 'forwarding_to_python', text, textPreview: text?.slice(0, 50) });
    const commandData = await PythonForwarder.buildCommandData(data, text);

    let acked = false;
    const messages = await PythonForwarder.requestPython(data, commandData, () => {
      acked = true;
    });
    if (messages === null) return;

    if (!messages) {
      if (acked) await TypingIndicator.stop(commandData.key.remoteJid!);
      return;
    }

    PythonForwarder.replaceQuotedRefs(messages, data);

    try {
      await sendBatch(messages);
    } catch (error) {
      PythonForwarder.captureException(error, commandData, text);
      await PythonForwarder.replyError(commandData);
    } finally {
      if (acked) await TypingIndicator.stop(commandData.key.remoteJid!);
    }
  }

  private static async buildCommandData(data: WAMessage, text: string): Promise<CommandData> {
    return {
      ...data,
      text,
      expiration: await GetGroupExpiration.run(data),
    } as CommandData;
  }

  private static async requestPython(
    raw: WAMessage,
    commandData: CommandData,
    markAcked: () => void,
  ): Promise<Message[] | null | undefined> {
    try {
      return await Resenhazord2.bridge.sendCommand(commandData, async () => {
        markAcked();
        await ReactMessage.run(raw);
        await TypingIndicator.start(commandData.key.remoteJid!);
      });
    } catch (error) {
      PythonForwarder.captureException(error, commandData, commandData.text);
      await PythonForwarder.replyError(commandData);
      return null;
    }
  }

  private static replaceQuotedRefs(messages: Message[], data: WAMessage): void {
    for (const msg of messages) {
      if (msg.options?.quoted) {
        msg.options.quoted = structuredClone(data) as WAMessage;
      }
    }
  }

  private static captureException(error: unknown, commandData: CommandData, text: string): void {
    Sentry.withScope((scope) => {
      scope.setTag('command', 'python');
      scope.setExtra('jid', commandData.key?.remoteJid);
      scope.setExtra('text', text?.slice(0, PythonForwarder.TEXT_PREVIEW_LENGTH));
      Sentry.captureException(error);
    });
  }

  private static async replyError(commandData: CommandData): Promise<void> {
    await Resenhazord2.adapter!.sendMessage(
      commandData.key.remoteJid!,
      { text: PythonForwarder.ERROR_TEXT },
      { quoted: commandData, ephemeralExpiration: commandData.expiration },
    );
  }
}
