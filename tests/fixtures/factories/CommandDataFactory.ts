import { Factory } from 'fishery';
import type { CommandData } from '../../../src/types/command.js';
import { WAMessageFactory } from './WAMessageFactory.js';

interface CommandDataTransientParams {
  isGroup: boolean;
  hasImageMessage: boolean;
  hasVideoMessage: boolean;
  hasAudioMessage: boolean;
  hasStickerMessage: boolean;
  hasQuotedMessage: boolean;
  mentionedJids: string[];
}

export const CommandDataFactory = Factory.define<CommandData, CommandDataTransientParams>(
  ({ transientParams, params }) => {
    const waMessage = WAMessageFactory.build({}, { transient: transientParams });

    return {
      ...waMessage,
      text: params.text ?? '',
      expiration: params.expiration,
    } as CommandData;
  },
);

export const GroupCommandData = CommandDataFactory.params({}).transient({ isGroup: true });

export const PrivateCommandData = CommandDataFactory.params({}).transient({ isGroup: false });

export const MentionCommandData = (mentionedJids: string[]) =>
  CommandDataFactory.params({}).transient({ isGroup: true, mentionedJids });
