import { proto } from '@whiskeysockets/baileys';
import UnsupportedGroupStatusError from './UnsupportedGroupStatusError.js';
import {
  STATUS_SOURCES,
  TEXT_BACKGROUNDS,
  TEXT_FONTS,
  VOICE_BACKGROUNDS,
  type StatusKind,
} from '../data/GroupStatusStyles.js';

type Content = { contextInfo?: proto.IContextInfo | null };

// Wraps message content the way the official client posts a group status: the real
// message inside groupStatusMessageV2, the secret on the wrapper, and a status context
// on the media. Voice notes carry no attributions, matching what the phone sends.
export default class GroupStatus {
  private static readonly SECRET_BYTES = 32;
  private static readonly TEXT_COLOR = 0xffffffff;

  constructor(
    private readonly authorJid: string,
    private readonly random: () => number = Math.random,
  ) {}

  wrap(content: proto.IMessage): proto.IMessage {
    const { messageContextInfo, ...message } = content;
    const kinds = Object.keys(message);
    const kind = kinds.find((key): key is StatusKind => key in STATUS_SOURCES);
    if (!kind) throw new UnsupportedGroupStatusError(kinds);
    const secret = messageContextInfo?.messageSecret;
    return {
      messageContextInfo: {
        messageSecret: secret ?? crypto.getRandomValues(new Uint8Array(GroupStatus.SECRET_BYTES)),
      },
      groupStatusMessageV2: { message: { [kind]: this.decorate(kind, message[kind]!) } },
    };
  }

  private decorate(kind: StatusKind, content: Content): Content & Record<string, unknown> {
    const contextInfo = this.contextInfo(kind, content.contextInfo);
    if (kind === 'audioMessage') {
      return { ...content, ptt: true, backgroundArgb: this.pick(VOICE_BACKGROUNDS), contextInfo };
    }
    if (kind === 'extendedTextMessage') {
      return {
        ...content,
        textArgb: GroupStatus.TEXT_COLOR,
        backgroundArgb: this.pick(TEXT_BACKGROUNDS),
        font: this.pick(TEXT_FONTS),
        contextInfo,
      };
    }
    return { ...content, contextInfo };
  }

  private contextInfo(kind: StatusKind, current?: proto.IContextInfo | null): proto.IContextInfo {
    const base = { ...current, isGroupStatus: true, statusSourceType: STATUS_SOURCES[kind] };
    if (kind === 'audioMessage') return base;
    const attribution = {
      type: proto.StatusAttribution.Type.GROUP_STATUS,
      groupStatus: { authorJid: this.authorJid },
    };
    return { ...base, statusAttributions: [attribution] };
  }

  private pick<T>(options: readonly T[]): T {
    return options[Math.floor(this.random() * options.length)];
  }
}
