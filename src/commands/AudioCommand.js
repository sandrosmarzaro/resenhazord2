import tts from 'google-tts-api';
import pkg from 'whatsapp-web.js';
const { MessageMedia } = pkg;

export default class AudioCommand {
    static async run(data) {
        console.log('AUDIO COMMAND');

        const chat = await data.getChat();
        const rest_command = data.body.replace(/\n*\s*\,\s*audio\s*/, '');
        const is_language_inserted = rest_command.match(/^[A-Z][a-z]\s*\-\s*[A-Z]{2}/);
        const language = is_language_inserted ? is_language_inserted[0] : 'Pt-BR';
        const languages = [
            'Af-ZA', 'Sq-AL', 'Am-ET', 'Ar-DZ', 'Ar-BH', 'Ar-EG', 'Ar-IQ', 'Ar-IL', 'Ar-JO', 'Ar-KW', 'Ar-LB',
            'Ar-MR', 'Ar-MA', 'Ar-OM', 'Ar-QA', 'Ar-SA', 'Ar-PS', 'Ar-TN', 'Ar-AE', 'Ar-YE', 'Hy-AM', 'Az-AZ',
            'Eu-ES', 'Bn-BD', 'Bn-IN', 'Bs-BA', 'Bg-BG', 'My-MM', 'Ca-ES', 'Hr-HR', 'Cs-CZ', 'Da-DK', 'Nl-BE',
            'Nl-NL', 'En-AU', 'En-CA', 'En-GH', 'En-HK', 'En-IN', 'En-IE', 'En-KE', 'En-NZ', 'En-NG', 'En-PK',
            'En-PH', 'En-SG', 'En-ZA', 'En-TZ', 'En-GB', 'En-US', 'Et-EE', 'Fil-PH', 'Fi-FI', 'Fr-BE', 'Fr-CA',
            'Fr-FR', 'Fr-CH', 'Gl-ES', 'Ka-GE', 'De-AT', 'De-DE', 'De-CH', 'El-GR', 'Gu-IN', 'Iw-IL', 'Hi-IN',
            'Hu-HU', 'Is-IS', 'Id-ID', 'It-IT', 'It-CH', 'Ja-JP', 'Jv-ID', 'Kn-IN', 'Kk-KZ', 'Km-KH', 'Ko-KR',
            'Lo-LA', 'Lv-LV', 'Lt-LT', 'Mk-MK', 'Ms-MY', 'Ml-IN', 'Mr-IN', 'Mn-MN', 'Ne-NP', 'No-NO', 'Fa-IR',
            'Pl-PL', 'Pt-BR', 'Pt-PT', 'Ro-RO', 'Ru-RU', 'Sr-RS', 'Si-LK', 'Sk-SK', 'Sl-SI', 'Es-AR', 'Es-BO',
            'Es-CL', 'Es-CO', 'Es-CR', 'Es-DO', 'Es-EC', 'Es-SV', 'Es-GT', 'Es-HN', 'Es-MX', 'Es-NI', 'Es-PA',
            'Es-PY', 'Es-PE', 'Es-PR', 'Es-ES', 'Es-US', 'Es-UY', 'Es-VE', 'Su-ID', 'Sw-KE', 'Sw-TZ', 'Sv-SE',
            'Ta-IN', 'Ta-MY', 'Ta-SG', 'Ta-LK', 'Te-IN', 'Th-TH', 'Tr-TR', 'Uk-UA', 'Ur-IN', 'Ur-PK', 'Uz-UZ',
            'Vi-VN', 'Zu-ZA', 'Zh-TW (cmn-Hant-TW)', 'Zh (cmn-Hans-CN)', 'Yue-Hant-HK', 'Pa-Guru-IN'
        ]
        if (!languages.includes(language)) {
            chat.sendMessage(
                'Burro burro! O idioma 🏳️‍🌈 não existe!',
                { sendSeen: true, quotedMessageId: data.id._serialized }
            );
            return;
        }
        let text;
        if (is_language_inserted) {
            text = rest_command.replace(is_language_inserted[0], '');
        }
        else {
            text = rest_command;
        }
        const audio_url = tts.getAudioUrl(text, {
            lang: language,
            slow: false,
            host: 'https://translate.google.com',
        });
        await chat.sendMessage(
            await MessageMedia.fromUrl(audio_url, { unsafeMime: true }),
            {
                sendSeen: true,
                sendAudioAsVoice: true,
                quotedMessageId: data.id._serialized,
            }
        );
    }
}