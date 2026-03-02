import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import { ArgType } from '../types/commandConfig.js';
import Command from './Command.js';
import { IMAGE_RESOLUTIONS } from '../data/imageResolutions.js';

export default class ImageCommand extends Command {
  readonly config: CommandConfig = {
    name: 'img',
    options: [
      { name: 'resolution', values: ['sd', 'hd', 'fhd', 'qhd', '4k'] },
      {
        name: 'model',
        values: ['flux-pro', 'flux-realism', 'flux-anime', 'flux-3d', 'flux', 'cablyai', 'turbo'],
      },
    ],
    flags: ['show', 'dm'],
    args: ArgType.Optional,
  };
  readonly menuDescription =
    'Gere uma imagem baseada no prompt usando IA com resolução e modelo opcionais.';

  protected async execute(data: CommandData, parsed: ParsedCommand): Promise<Message[]> {
    const seed = (): number => new Date().getTime() % 1000000;
    const resolution = parsed.options.get('resolution') || null;
    const model = parsed.options.get('model') || null;
    const prompt = parsed.rest.trim();

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

    return [
      {
        jid: data.key.remoteJid!,
        content: { image: { url: imageUrl }, viewOnce: true },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
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
