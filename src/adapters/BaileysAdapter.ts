import type {
  AnyMessageContent,
  GroupMetadata,
  MiscMessageGenerationOptions,
  WAMessage,
  WASocket,
} from '@whiskeysockets/baileys';
import type WhatsAppPort from '../ports/WhatsAppPort.js';

export default class BaileysAdapter implements WhatsAppPort {
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
}
