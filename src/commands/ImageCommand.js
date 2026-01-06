import Resenhazord2 from '../models/Resenhazord2.js';

export default class ImageCommand {

    static identifier = "^\\s*\\,\\s*img\\s*(?:sd|hd|fhd|qhd|4k)?\\s*(?:(?:flux)?(?:-pro|-realism|-anime|-3d|cablyai)?)?(?:turbo)?\\s*(?:show)?\\s*(?:dm)?\\s*";

    static async run(data) {
        const seed = () => new Date().getTime() % 1000000;
        const { resolution, model, prompt } = this.parseCommand(data.text);

        if (!prompt) {
            await Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: 'Você precisa informar um texto para a imagem! 🤷‍♂️'},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
            return;
        }

        const resolution_mappping = {
            'sd': [768, 768],
            'hd': [720, 1280],
            'fhd': [1080, 1920],
            'qhd': [1440, 2560],
            '4k': [2160, 3840]
        }
        const [width, height] = resolution_mappping[resolution] || [768, 768];

        const imageUrl = this.generateImageUrl(prompt, width, height, model, seed);

        let chat_id = data.key.remoteJid
        const DM_FLAG_ACTIVE = data.text.match(/dm/)
        if (DM_FLAG_ACTIVE && data.key.participant) {
            chat_id = data.key.participant
        }
        await Resenhazord2.socket.sendMessage(
            chat_id,
            {image: {url: imageUrl}, viewOnce: !(data.text.match(/show/))},
            {quoted: data, ephemeralExpiration: data.expiration}
        );
    }

    static parseCommand(text) {
        const text_without_prefix = text.replace(/^\s*\,\s*img\s*/, '');

        const resolution = text_without_prefix.match(/^(sd|hd|fhd|qhd|4k)/);
        const text_without_prefix_and_resolution = text_without_prefix.replace(/^(sd|hd|fhd|qhd|4k)/, '');

        const model = text_without_prefix_and_resolution.match(/^(?:flux)?(?:-pro|-realism|-anime|-3d|cablyai)?/);
        const prompt = text_without_prefix_and_resolution.replace(/^(?:flux)?(?:-pro|-realism|-anime|-3d|cablyai)?/, '');

        return { resolution, model, prompt };
    }

    static generateImageUrl(prompt, width = 768, height = 768, model = 'flux', seed) {

        return `https://pollinations.ai/p/${encodeURIComponent(prompt)}?width=${width}&height=${height}&seed=${seed}&model=${model}`;
    }

}