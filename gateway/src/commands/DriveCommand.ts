import type { WAMessage } from '@whiskeysockets/baileys';
import Command, {
  type CommandData,
  type CommandConfig,
  type ParsedCommand,
  type Message,
  type WhatsAppPort,
  ArgType,
} from './Command.js';
import { downloadMediaMessage } from '@whiskeysockets/baileys';
import pino from 'pino';
import Reply from '../builders/Reply.js';
import DiscordService from '../clients/DiscordService.js';
import { Sentry } from '../infra/Sentry.js';

const MEDIA_TYPES = ['imageMessage', 'videoMessage', 'audioMessage'] as const;
type MediaType = (typeof MEDIA_TYPES)[number];

const EXTENSIONS: Record<MediaType, string> = {
  imageMessage: 'jpg',
  videoMessage: 'mp4',
  audioMessage: 'ogg',
};

const TYPE_LABEL: Record<MediaType, string> = {
  imageMessage: 'image',
  videoMessage: 'video',
  audioMessage: 'audio',
};

type AnyMsg = Record<string, unknown>;

function findDirectMedia(data: CommandData): { message: WAMessage; type: MediaType } | null {
  const msg = data.message as AnyMsg | undefined;
  if (!msg) return null;
  for (const type of MEDIA_TYPES) {
    if (msg[type]) return { message: data as WAMessage, type };
  }
  return null;
}

function findQuotedMedia(data: CommandData): { message: WAMessage; type: MediaType } | null {
  const quoted = data.message?.extendedTextMessage?.contextInfo?.quotedMessage as
    | AnyMsg
    | undefined;
  if (!quoted) return null;
  for (const type of MEDIA_TYPES) {
    if (quoted[type]) {
      const wrappedQuoted: WAMessage = {
        key: data.key,
        message: data.message?.extendedTextMessage?.contextInfo?.quotedMessage ?? null,
      };
      return { message: wrappedQuoted, type };
    }
  }
  return null;
}

export default class DriveCommand extends Command {
  readonly config: CommandConfig = {
    name: 'drive',
    flags: ['new'],
    args: ArgType.Required,
    groupOnly: true,
    category: 'grupo',
  };
  readonly menuDescription = 'Arquiva uma mídia no Discord. Use: ,drive <categoria> <canal>';

  constructor(
    whatsapp?: WhatsAppPort,
    private readonly discord?: DiscordService,
  ) {
    super(whatsapp);
  }

  protected async execute(data: CommandData, parsed: ParsedCommand): Promise<Message[]> {
    const parts = parsed.rest.trim().split(/\s+/);
    if (parts.length < 2) {
      return [Reply.to(data).text('Uso: ,drive <categoria> <canal>')];
    }

    const category = parts[0];
    const channel = parts.slice(1).join(' ');
    const isNew = parsed.flags.has('new');

    const mediaResult = findDirectMedia(data) ?? findQuotedMedia(data);
    if (!mediaResult) {
      return [
        Reply.to(data).text(
          'Nenhuma mídia encontrada. Envie ou marque uma imagem, vídeo ou áudio.',
        ),
      ];
    }

    try {
      const channels = await this.discord!.getChannels();

      let categoryChannel = DiscordService.findCategory(channels, category);
      if (!categoryChannel) {
        if (!isNew) {
          return [
            Reply.to(data).text(
              `Categoria *${category}* não encontrada. Use a flag \`new\` para criar.`,
            ),
          ];
        }
        categoryChannel = await this.discord!.createCategory(category);
      }

      let targetChannel = DiscordService.findChannel(channels, channel, categoryChannel.id);
      if (!targetChannel) {
        if (!isNew) {
          return [
            Reply.to(data).text(
              `Canal *${channel}* não encontrado em *${category}*. Use a flag \`new\` para criar.`,
            ),
          ];
        }
        targetChannel = await this.discord!.createChannel(channel, categoryChannel.id);
      }

      const buffer = await downloadMediaMessage(
        mediaResult.message,
        'buffer',
        {},
        {
          reuploadRequest: this.whatsapp!.updateMediaMessage,
          logger: pino({ level: 'silent' }),
        },
      );

      const timestamp = Date.now();
      const ext = EXTENSIONS[mediaResult.type];
      const label = TYPE_LABEL[mediaResult.type];
      const filename = `${label}_${timestamp}.${ext}`;

      await this.discord!.uploadMedia(targetChannel.id, buffer as Buffer, filename);

      return [Reply.to(data).text(`✅ Mídia salva em *${category}* > *#${channel}*`)];
    } catch (error) {
      Sentry.captureException(error, { extra: { category, channel, isNew } });
      return [Reply.to(data).text('Erro ao salvar no Drive 📁')];
    }
  }
}
