import type {
  AnyMessageContent,
  MiscMessageGenerationOptions,
  WAPresence,
} from '@whiskeysockets/baileys';
import type BrokerPort from '../ports/BrokerPort.js';
import type WhatsAppPort from '../ports/WhatsAppPort.js';

interface WaAction {
  method: string;
  jid: string;
  participants?: string[];
  action?: 'add' | 'remove' | 'promote' | 'demote';
  content?: AnyMessageContent;
  options?: MiscMessageGenerationOptions;
  image?: string;
  subject?: string;
  description?: string;
  type?: WAPresence;
}

export default class WaActionConsumer {
  private static readonly QUEUE = 'wa_actions';

  constructor(
    private readonly broker: BrokerPort,
    private readonly whatsapp: WhatsAppPort,
  ) {}

  async start(): Promise<void> {
    await this.broker.consume(WaActionConsumer.QUEUE, (body) => this.handle(body));
  }

  private async handle(body: Buffer): Promise<void> {
    const action = JSON.parse(body.toString()) as WaAction;
    const handler = this.handlers(action)[action.method];
    if (!handler) throw new Error(`Unknown wa_action method: ${action.method}`);
    await handler();
  }

  private handlers(action: WaAction): Record<string, () => Promise<unknown>> {
    return {
      group_participants_update: () =>
        this.whatsapp.groupParticipantsUpdate(
          action.jid,
          action.participants ?? [],
          action.action ?? 'remove',
        ),
      send_message: () =>
        this.whatsapp.sendMessage(action.jid, action.content as AnyMessageContent, action.options),
      update_profile_picture: () =>
        this.whatsapp.updateProfilePicture(action.jid, Buffer.from(action.image ?? '', 'base64')),
      group_update_subject: () =>
        this.whatsapp.groupUpdateSubject(action.jid, action.subject ?? ''),
      group_update_description: () =>
        this.whatsapp.groupUpdateDescription(action.jid, action.description ?? ''),
      send_presence_update: () =>
        this.whatsapp.sendPresenceUpdate(action.type ?? 'available', action.jid),
    };
  }
}
