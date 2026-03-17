import type {
  AnyMessageContent,
  GroupMetadata,
  MiscMessageGenerationOptions,
  WAMessage,
  WAPresence,
} from '@whiskeysockets/baileys';

export default interface WhatsAppPort {
  sendMessage(
    jid: string,
    content: AnyMessageContent,
    options?: MiscMessageGenerationOptions,
  ): Promise<WAMessage | undefined>;

  groupMetadata(jid: string): Promise<GroupMetadata>;

  groupParticipantsUpdate(
    jid: string,
    participants: string[],
    action: 'add' | 'remove' | 'promote' | 'demote',
  ): Promise<unknown[]>;

  groupUpdateSubject(jid: string, subject: string): Promise<void>;

  groupUpdateDescription(jid: string, description: string): Promise<void>;

  updateProfilePicture(jid: string, content: Buffer): Promise<void>;

  onWhatsApp(...jids: string[]): Promise<{ exists: boolean; jid: string }[]>;

  updateMediaMessage(message: WAMessage): Promise<WAMessage>;

  sendPresenceUpdate(type: WAPresence, jid: string): Promise<void>;
}
