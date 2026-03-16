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

export default class CommandHandler {
  static async run(data: WAMessage): Promise<void> {
    const text = GetTextMessage.run(data);
    const factory = CommandFactory.getInstance(Resenhazord2.adapter ?? undefined);
    const command = factory.getStrategy(text);

    if (command) {
      await this.executeCommand(data, text, command.constructor.name, (commandData) =>
        command.run(commandData),
      );
      return;
    }

    if (Resenhazord2.bridge.isConnected) {
      const commandData = {
        ...data,
        text,
        expiration: await GetGroupExpiration.run(data),
      } as CommandData;

      let messages: Message[] | null;
      try {
        messages = await Resenhazord2.bridge.sendCommand(commandData);
      } catch {
        return;
      }

      if (messages) {
        for (const msg of messages) {
          if (msg.options?.quoted) {
            msg.options.quoted = data;
          }
        }
        await ReactMessage.run(data);
        await TypingIndicator.start(commandData.key.remoteJid!);
        try {
          await this.sendMessages(messages);
        } finally {
          await TypingIndicator.stop(commandData.key.remoteJid!);
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

  private static async sendMessages(messages: Message[]): Promise<void> {
    for (const msg of messages) {
      await Resenhazord2.adapter!.sendMessage(msg.jid, msg.content, msg.options);
    }
  }
}
