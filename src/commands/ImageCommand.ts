import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import { IMAGE_RESOLUTIONS } from '../data/imageResolutions.js';

export default class ImageCommand extends Command {
  readonly regexIdentifier =
    '^\\s*\\,\\s*img\\s*(?:sd|hd|fhd|qhd|4k)?\\s*(?:(?:flux)?(?:-pro|-realism|-anime|-3d|cablyai)?)?(?:turbo)?\\s*(?:show)?\\s*(?:dm)?\\s*';
  readonly menuDescription =
    'Gere uma imagem baseada no prompt usando IA com resolução e modelo opcionais.';

  async run(data: CommandData): Promise<Message[]> {
    const seed = (): number => new Date().getTime() % 1000000;
    const { resolution, model, prompt } = this.parseCommand(data.text);

    if (!prompt) {
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: 'Você precisa informar um texto para a imagem! 🤷‍♂️' },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }

    const [width, height] = (resolution ? IMAGE_RESOLUTIONS[resolution] : null) || [768, 768];

    const imageUrl = this.generateImageUrl(prompt, width, height, model, seed());

    let chat_id: string = data.key.remoteJid!;
    const DM_FLAG_ACTIVE = data.text.match(/dm/);
    if (DM_FLAG_ACTIVE && data.key.participant) {
      chat_id = data.key.participant;
    }
    return [
      {
        jid: chat_id,
        content: { image: { url: imageUrl }, viewOnce: !data.text.match(/show/) },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }

  private parseCommand(text: string): {
    resolution: string | null;
    model: string | null;
    prompt: string;
  } {
    const text_without_prefix = text.replace(/^\s*,\s*img\s*/, '');

    const resolutionMatch = text_without_prefix.match(/^(sd|hd|fhd|qhd|4k)/);
    const resolution = resolutionMatch ? resolutionMatch[0] : null;
    const text_without_prefix_and_resolution = text_without_prefix.replace(
      /^(sd|hd|fhd|qhd|4k)/,
      '',
    );

    const modelMatch = text_without_prefix_and_resolution.match(
      /^(?:flux)?(?:-pro|-realism|-anime|-3d|cablyai)?/,
    );
    const model = modelMatch ? modelMatch[0] : null;
    const prompt = text_without_prefix_and_resolution.replace(
      /^(?:flux)?(?:-pro|-realism|-anime|-3d|cablyai)?/,
      '',
    );

    return { resolution, model, prompt };
  }

  private generateImageUrl(
    prompt: string,
    width = 768,
    height = 768,
    model: string | null = 'flux',
    seed: number,
  ): string {
    return `https://pollinations.ai/p/${encodeURIComponent(prompt)}?width=${width}&height=${height}&seed=${seed}&model=${model}`;
  }
}
