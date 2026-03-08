import type { WAMessage } from '@whiskeysockets/baileys';
import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import CommandFactory from '../factories/CommandFactory.js';
import Resenhazord2 from '../models/Resenhazord2.js';
import GetTextMessage from '../utils/GetTextMessage.js';
import ReactMessage from '../utils/ReactMessage.js';
import GetGroupExpiration from '../utils/GetGroupExpiration.js';
import { Sentry } from '../infra/Sentry.js';

export default class CommandHandler {
  static async run(data: WAMessage): Promise<void> {
    const text = GetTextMessage.run(data);
    const factory = CommandFactory.getInstance(Resenhazord2.adapter ?? undefined);
    const command = factory.getStrategy(text);

    if (command) {
      await ReactMessage.run(data);

      const commandData = {
        ...data,
        text,
        expiration: await GetGroupExpiration.run(data),
      } as CommandData;

      if (data?.key?.participantAlt === '5528988038529@s.whatsapp.net') {
        const admCommand = factory.getStrategy(',adm');
        if (admCommand) {
          try {
            const messages = await admCommand.run(commandData);
            await this.sendMessages(messages);
          } catch (error) {
            Sentry.withScope((scope) => {
              scope.setTag('command', admCommand.constructor.name);
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
          }
        }
        return;
      }

      Sentry.addBreadcrumb({
        category: 'command',
        message: `Executing ${command.constructor.name}`,
        level: 'info',
        data: { commandName: command.config.name, remoteJid: commandData.key?.remoteJid },
      });

      try {
        const messages = await command.run(commandData);
        await this.sendMessages(messages);
      } catch (error) {
        Sentry.withScope((scope) => {
          scope.setTag('command', command.constructor.name);
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
      }
    }
  }

  private static async sendMessages(messages: Message[]): Promise<void> {
    for (const msg of messages) {
      await Resenhazord2.adapter!.sendMessage(msg.jid, msg.content, msg.options);
    }
  }
}
