import type { WAMessage } from '@whiskeysockets/baileys';
import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import BotMentionDetector from './BotMentionDetector.js';
import CommandFactory from '../factories/CommandFactory.js';
import PythonForwarder from './PythonForwarder.js';
import Resenhazord2 from '../models/Resenhazord2.js';
import GetTextMessage from '../utils/GetTextMessage.js';
import GetGroupExpiration from '../utils/GetGroupExpiration.js';
import ReactMessage from '../utils/ReactMessage.js';
import TypingIndicator from '../utils/TypingIndicator.js';
import { Sentry } from '../infra/Sentry.js';
import logger from '../infra/Logger.js';

export default class CommandHandler {
  private static readonly BATCH_DELAY_MS = 1000;
  private static readonly ERROR_TEXT = 'Ocorreu um erro ao processar o comando 😔';
  private static readonly TEXT_PREVIEW_LENGTH = 200;

  static async run(data: WAMessage): Promise<void> {
    const text = GetTextMessage.run(data);
    const command = CommandFactory.getInstance().getStrategy(text);

    if (command) {
      await CommandHandler.executeCommand(data, text, command.constructor.name, (commandData) =>
        command.run(commandData),
      );
      return;
    }

    if (!CommandHandler.shouldForward(data, text)) return;
    await PythonForwarder.forward(data, text, CommandHandler.sendMessages);
  }

  private static shouldForward(data: WAMessage, text: string): boolean {
    const isDM = !data.key.remoteJid?.includes('@g.us');
    const startsWithComma = text?.trimStart().startsWith(',');
    const mentionsBot = BotMentionDetector.mentionsBot(data, text);

    logger.debug({
      event: 'mention_forward_check',
      isConnected: Resenhazord2.bridge.isConnected,
      startsWithComma,
      mentionsBot,
      isDM,
      text: text?.slice(0, 50),
    });

    return Resenhazord2.bridge.isConnected && (startsWithComma || mentionsBot || isDM);
  }

  private static async executeCommand(
    data: WAMessage,
    text: string,
    commandName: string,
    executor: (commandData: CommandData) => Promise<Message[]>,
  ): Promise<void> {
    await ReactMessage.run(data);

    const commandData = {
      ...data,
      text,
      expiration: await GetGroupExpiration.run(data),
    } as CommandData;

    await TypingIndicator.start(commandData.key.remoteJid!);

    Sentry.addBreadcrumb({
      category: 'command',
      message: `Executing ${commandName}`,
      level: 'info',
      data: { commandName, remoteJid: commandData.key?.remoteJid },
    });

    try {
      const messages = await executor(commandData);
      await CommandHandler.sendMessages(messages);
    } catch (error) {
      Sentry.withScope((scope) => {
        scope.setTag('command', commandName);
        scope.setExtra('jid', commandData.key?.remoteJid);
        scope.setExtra('participant', commandData.key?.participant);
        scope.setExtra('text', commandData.text?.slice(0, CommandHandler.TEXT_PREVIEW_LENGTH));
        Sentry.captureException(error);
      });
      await Resenhazord2.adapter!.sendMessage(
        commandData.key.remoteJid!,
        { text: CommandHandler.ERROR_TEXT },
        { quoted: commandData, ephemeralExpiration: commandData.expiration },
      );
    } finally {
      await TypingIndicator.stop(commandData.key.remoteJid!);
    }
  }

  private static async sendMessages(messages: Message[]): Promise<void> {
    for (let i = 0; i < messages.length; i++) {
      if (i > 0) await new Promise((r) => setTimeout(r, CommandHandler.BATCH_DELAY_MS));
      const msg = messages[i];
      await Resenhazord2.adapter!.sendMessage(msg.jid, msg.content, msg.options);
    }
  }
}
