import type { CommandData } from '../types/command.js';
import Resenhazord2 from '../models/Resenhazord2.js';

export default class ImageCommand {
  static identifier: string =
    '^\\s*\\,\\s*img\\s*(?:sd|hd|fhd|qhd|4k)?\\s*(?:(?:flux)?(?:-pro|-realism|-anime|-3d|cablyai)?)?(?:turbo)?\\s*(?:show)?\\s*(?:dm)?\\s*';

  static async run(data: CommandData): Promise<void> {
    const seed = (): number => new Date().getTime() % 1000000;
    const { resolution, model, prompt } = this.parseCommand(data.text);

    if (!prompt) {
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: 'Você precisa informar um texto para a imagem! 🤷‍♂️' },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
      return;
    }

    const resolution_mappping: Record<string, [number, number]> = {
      sd: [768, 768],
      hd: [720, 1280],
      fhd: [1080, 1920],
      qhd: [1440, 2560],
      '4k': [2160, 3840],
    };
    const [width, height] = (resolution ? resolution_mappping[resolution] : null) || [768, 768];

    const imageUrl = this.generateImageUrl(prompt, width, height, model, seed());

    let chat_id: string = data.key.remoteJid!;
    const DM_FLAG_ACTIVE = data.text.match(/dm/);
    if (DM_FLAG_ACTIVE && data.key.participant) {
      chat_id = data.key.participant;
    }
    await Resenhazord2.socket!.sendMessage(
      chat_id,
      { image: { url: imageUrl }, viewOnce: !data.text.match(/show/) },
      { quoted: data, ephemeralExpiration: data.expiration },
    );
  }

  static parseCommand(text: string): {
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

  static generateImageUrl(
    prompt: string,
    width = 768,
    height = 768,
    model: string | null = 'flux',
    seed: number,
  ): string {
    return `https://pollinations.ai/p/${encodeURIComponent(prompt)}?width=${width}&height=${height}&seed=${seed}&model=${model}`;
  }
}
