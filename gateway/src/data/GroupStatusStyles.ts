import { proto } from '@whiskeysockets/baileys';

const Font = proto.Message.ExtendedTextMessage.FontType;
const Source = proto.ContextInfo.StatusSourceType;

export type StatusKind = 'extendedTextMessage' | 'imageMessage' | 'videoMessage' | 'audioMessage';

export const STATUS_SOURCES: Readonly<Record<StatusKind, proto.ContextInfo.StatusSourceType>> = {
  extendedTextMessage: Source.TEXT,
  imageMessage: Source.IMAGE,
  videoMessage: Source.VIDEO,
  audioMessage: Source.AUDIO,
};

export const TEXT_BACKGROUNDS: readonly number[] = [
  0xff7e57c2, 0xff57c9ff, 0xff26a69a, 0xffef5350, 0xffff8a65, 0xff5c6bc0, 0xff8d6e63, 0xff263238,
];

export const TEXT_FONTS: readonly proto.Message.ExtendedTextMessage.FontType[] = [
  Font.SYSTEM,
  Font.FB_SCRIPT,
  Font.SYSTEM_BOLD,
  Font.MORNINGBREEZE_REGULAR,
  Font.CALISTOGA_REGULAR,
  Font.EXO2_EXTRABOLD,
  Font.COURIERPRIME_BOLD,
];

export const VOICE_BACKGROUNDS: readonly number[] = [
  0xffb6b327, 0xff7e57c2, 0xff26a69a, 0xffef5350,
];
