import { Factory } from 'fishery';
import type { GroupMetadata, GroupParticipant } from '@whiskeysockets/baileys';

interface GroupMetadataTransientParams {
  isBotAdmin: boolean;
  participantCount: number;
}

export const GroupMetadataFactory = Factory.define<GroupMetadata, GroupMetadataTransientParams>(
  ({ transientParams, sequence }) => {
    const { isBotAdmin = false, participantCount = 5 } = transientParams;
    const botJid = process.env.RESENHAZORD2_JID ?? '5500000000000@s.whatsapp.net';

    const participants: GroupParticipant[] = [];

    participants.push({
      id: botJid,
      admin: isBotAdmin ? 'admin' : null,
    });

    for (let i = 0; i < participantCount - 1; i++) {
      participants.push({
        id: `5511${900000000 + i}@s.whatsapp.net`,
        admin: i === 0 ? 'admin' : null,
      });
    }

    return {
      id: `${120363000000000000 + sequence}@g.us`,
      subject: `Test Group ${sequence}`,
      owner: `5511${900000000}@s.whatsapp.net`,
      creation: Math.floor(Date.now() / 1000),
      participants,
    };
  },
);

export const GroupWithBotAdmin = GroupMetadataFactory.transient({ isBotAdmin: true });

export const GroupWithoutBotAdmin = GroupMetadataFactory.transient({ isBotAdmin: false });
