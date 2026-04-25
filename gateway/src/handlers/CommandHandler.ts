import type { WAMessage } from '@whiskeysockets/baileys';
import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import CommandFactory from '../factories/CommandFactory.js';
import Resenhazord2 from '../models/Resenhazord2.js';
import GetTextMessage from '../utils/GetTextMessage.js';
import ReactMessage from '../utils/ReactMessage.js';
import GetGroupExpiration from '../utils/GetGroupExpiration.js';
import TypingIndicator from '../utils/TypingIndicator.js';
import { Sentry } from '../infra/Sentry.js';
import logger from '../infra/Logger.js';

const RESENHA_JID = process.env.RESENHA_JID!;
const RESENHAZORD2_JID = process.env.RESENHAZORD2_JID!;
const RESENHAZORD2_LID = process.env.RESENHAZORD2_LID!;

function isBotId(id?: string): boolean {
  if (!id) return false;
  // Handle both full JID (@s.whatsapp.net or @g.us) and just the numeric part
  const numericPart = id.split('@')[0];
  return (
    numericPart === RESENHAZORD2_JID.split('@')[0] ||
    numericPart === RESENHA_JID.split('@')[0] ||
    numericPart === RESENHAZORD2_LID
  );
}

function hasResenhazordMention(data: WAMessage, text: string): boolean {
  if (!text) return false;
  const textLower = text.toLowerCase();
  const mentionedJids = data.message?.extendedTextMessage?.contextInfo?.mentionedJid ?? [];

  const hasJidMention = mentionedJids.some(isBotId);
  const hasTextMention = [
    RESENHAZORD2_JID?.split('@')[0],
    RESENHA_JID?.split('@')[0],
    RESENHAZORD2_LID,
  ].filter(Boolean).some((botId) => textLower.includes(botId.toLowerCase()));

  const hasAnyMention = mentionedJids.length > 0;

  logger.debug({
    event: 'mention_check',
    mentionedJids,
    hasJidMention,
    hasTextMention,
    hasAnyMention,
    text: textLower,
  });

  return hasJidMention || hasTextMention || hasAnyMention;
}

export default class CommandHandler {
  static async run(data: WAMessage): Promise<void> {
    const text = GetTextMessage.run(data);
    const factory = CommandFactory.getInstance();
    const command = factory.getStrategy(text);

    if (command) {
      await this.executeCommand(data, text, command.constructor.name, (commandData) =>
        command.run(commandData),
      );
      return;
    }

    const isDM = !data.key.remoteJid?.includes('@g.us');
    logger.debug({
      event: 'mention_forward_check',
      isConnected: Resenhazord2.bridge.isConnected,
      startsWithComma: text?.trimStart().startsWith(','),
      mentionsBot: hasResenhazordMention(data, text),
      isDM,
      text: text?.slice(0, 50),
    });
    if (
      Resenhazord2.bridge.isConnected &&
      (text?.trimStart().startsWith(',') || hasResenhazordMention(data, text) || isDM)
    ) {
      const commandData = {
        ...data,
        text,
        expiration: await GetGroupExpiration.run(data),
      } as CommandData;

      let acked = false;
      let messages: Message[] | null;
      try {
        messages = await Resenhazord2.bridge.sendCommand(commandData, async () => {
          acked = true;
          await ReactMessage.run(data);
          await TypingIndicator.start(commandData.key.remoteJid!);
        });
      } catch (error) {
        Sentry.withScope((scope) => {
          scope.setTag('command', 'python');
          scope.setExtra('jid', commandData.key?.remoteJid);
          scope.setExtra('text', text?.slice(0, 200));
          Sentry.captureException(error);
        });
        await Resenhazord2.adapter!.sendMessage(
          commandData.key.remoteJid!,
          { text: 'Ocorreu um erro ao processar o comando 😔' },
          { quoted: commandData, ephemeralExpiration: commandData.expiration },
        );
        if (acked) await TypingIndicator.stop(commandData.key.remoteJid!);
        return;
      }

      if (messages) {
        for (const msg of messages) {
          if (msg.options?.quoted) {
            msg.options.quoted = structuredClone(data) as WAMessage;
          }
        }
        try {
          await this.sendMessages(messages);
        } catch (error) {
          Sentry.withScope((scope) => {
            scope.setTag('command', 'python');
            scope.setExtra('jid', commandData.key?.remoteJid);
            scope.setExtra('text', text?.slice(0, 200));
            Sentry.captureException(error);
          });
          await Resenhazord2.adapter!.sendMessage(
            commandData.key.remoteJid!,
            { text: 'Ocorreu um erro ao processar o comando 😔' },
            { quoted: commandData, ephemeralExpiration: commandData.expiration },
          );
        } finally {
          if (acked) await TypingIndicator.stop(commandData.key.remoteJid!);
        }
      }
    }
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
      await this.sendMessages(messages);
    } catch (error) {
      Sentry.withScope((scope) => {
        scope.setTag('command', commandName);
        scope.setExtra('jid', commandData.key?.remoteJid);
        scope.setExtra('participant', commandData.key?.participant);
        scope.setExtra('text', commandData.text?.slice(0, 200));
        Sentry.captureException(error);
      });
      await Resenhazord2.adapter!.sendMessage(
        commandData.key.remoteJid!,
        { text: 'Ocorreu um erro ao processar o comando 😔' },
        { quoted: commandData, ephemeralExpiration: commandData.expiration },
      );
    } finally {
      await TypingIndicator.stop(commandData.key.remoteJid!);
    }
  }

  private static readonly BATCH_DELAY_MS = 1000;

  private static async sendMessages(messages: Message[]): Promise<void> {
    for (let i = 0; i < messages.length; i++) {
      if (i > 0) await new Promise((r) => setTimeout(r, CommandHandler.BATCH_DELAY_MS));
      const msg = messages[i];
      await Resenhazord2.adapter!.sendMessage(msg.jid, msg.content, msg.options);
    }
  }
}
