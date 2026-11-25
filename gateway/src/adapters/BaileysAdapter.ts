import type {
  AnyMessageContent,
  GroupMetadata,
  MiscMessageGenerationOptions,
  WAMessage,
  WAMessageKey,
  WAPresence,
  WASocket,
} from '@whiskeysockets/baileys';
import {
  generateWAMessageContent,
  jidNormalizedUser,
  prepareWAMessageMedia,
} from '@whiskeysockets/baileys';
import type WhatsAppPort from '../ports/WhatsAppPort.js';
import GroupStatus from '../builders/GroupStatus.js';

export default class BaileysAdapter implements WhatsAppPort {
  // What WhatsApp itself sends for a chat muted 'Always'.
  private static readonly MUTE_FOREVER = -1;
  // What WhatsApp's own audio stickers carry, and what plays on Web and Android.
  private static readonly STICKER_AUDIO_MIMETYPE = 'audio/ogg; codecs=opus';
  // An extended (VP8X) webp header, and its animation flag in the feature byte.
  private static readonly WEBP_EXTENDED = 'VP8X';
  private static readonly WEBP_FEATURES_OFFSET = 20;
  private static readonly WEBP_ANIMATION_FLAG = 0x02;
  private readonly socket: WASocket;
  readonly updateMediaMessage: (message: WAMessage) => Promise<WAMessage>;

  constructor(socket: WASocket) {
    this.socket = socket;
    this.updateMediaMessage = socket.updateMediaMessage.bind(socket);
  }

  async sendMessage(
    jid: string,
    content: AnyMessageContent,
    options?: MiscMessageGenerationOptions,
  ): Promise<WAMessage | undefined> {
    return this.socket.sendMessage(jid, content, options);
  }

  async sendGroupStatus(jid: string, content: AnyMessageContent): Promise<void> {
    const message = await generateWAMessageContent(content, {
      upload: this.socket.waUploadToServer,
    });
    const author = jidNormalizedUser(this.socket.user?.lid);
    await this.socket.relayMessage(jid, new GroupStatus(author).wrap(message), {});
  }

  // The audio rides inside the stickerMessage, which no AnyMessageContent builds: upload
  // both, then send the proto as a forward of the bot's own message, which Baileys
  // copies unmarked while still applying quoting and disappearing messages.
  async sendAudioSticker(
    jid: string,
    sticker: Buffer,
    audio: Buffer,
    options?: MiscMessageGenerationOptions,
  ): Promise<WAMessage | undefined> {
    const upload = { upload: this.socket.waUploadToServer };
    const [{ stickerMessage }, { audioMessage }] = await Promise.all([
      prepareWAMessageMedia({ sticker }, upload),
      prepareWAMessageMedia({ audio, mimetype: BaileysAdapter.STICKER_AUDIO_MIMETYPE }, upload),
    ]);
    const isAnimated = BaileysAdapter.isAnimatedWebp(sticker);
    const message = { stickerMessage: { ...stickerMessage, isAnimated, audioMessage } };
    return this.socket.sendMessage(jid, { forward: { key: { fromMe: true }, message } }, options);
  }

  private static isAnimatedWebp(webp: Buffer): boolean {
    const extended = webp.toString('ascii', 12, 16) === BaileysAdapter.WEBP_EXTENDED;
    const features = webp[BaileysAdapter.WEBP_FEATURES_OFFSET];
    return extended && (features & BaileysAdapter.WEBP_ANIMATION_FLAG) !== 0;
  }

  async groupMetadata(jid: string): Promise<GroupMetadata> {
    return this.socket.groupMetadata(jid);
  }

  async groupParticipantsUpdate(
    jid: string,
    participants: string[],
    action: 'add' | 'remove' | 'promote' | 'demote',
  ): Promise<unknown[]> {
    return this.socket.groupParticipantsUpdate(jid, participants, action);
  }

  async groupUpdateSubject(jid: string, subject: string): Promise<void> {
    await this.socket.groupUpdateSubject(jid, subject);
  }

  async groupUpdateDescription(jid: string, description: string): Promise<void> {
    await this.socket.groupUpdateDescription(jid, description);
  }

  async updateProfilePicture(jid: string, content: Buffer): Promise<void> {
    await this.socket.updateProfilePicture(jid, content);
  }

  async onWhatsApp(...jids: string[]): Promise<{ exists: boolean; jid: string }[]> {
    return (await this.socket.onWhatsApp(...jids)) ?? [];
  }

  async sendPresenceUpdate(type: WAPresence, jid: string): Promise<void> {
    await this.socket.sendPresenceUpdate(type, jid);
  }

  async rejectCall(callId: string, callFrom: string): Promise<void> {
    await this.socket.rejectCall(callId, callFrom);
  }

  async readMessages(keys: WAMessageKey[]): Promise<void> {
    await this.socket.readMessages(keys);
  }

  async muteChat(jid: string): Promise<void> {
    await this.socket.chatModify({ mute: BaileysAdapter.MUTE_FOREVER }, jid);
  }
}
