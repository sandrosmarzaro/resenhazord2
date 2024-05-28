import tts from 'google-tts-api';
import pkg from 'whatsapp-web.js';
const { MessageMedia } = pkg;

export default class AudioCommand {
    static async run(data) {
        console.log('AUDIO COMMAND');

        const chat = await data.getChat();
        const rest_command = data.body.replace(/\n*\s*\,\s*.udio\s*/, '');
        const is_language_inserted = rest_command.match(/^[A-Za-z]{2}\s*\-\s*[A-Za-z]{2}/);
        const language = is_language_inserted ? is_language_inserted[0] : 'pt-br';
        const languages = [
            'af-za', 'sq-al', 'am-et', 'ar-dz', 'ar-bh', 'ar-eg', 'ar-iq', 'ar-il', 'ar-jo', 'ar-kw', 'ar-lb', 'ar-mr',
            'ar-ma', 'ar-om', 'ar-qa', 'ar-sa', 'ar-ps', 'ar-tn', 'ar-ae', 'ar-ye', 'hy-am', 'az-az', 'eu-es', 'bn-bd',
            'bn-in', 'bs-ba', 'bg-bg', 'my-mm', 'ca-es', 'hr-hr', 'cs-cz', 'da-dk', 'nl-be', 'nl-nl', 'en-au', 'en-ca',
            'en-gh', 'en-hk', 'en-in', 'en-ie', 'en-ke', 'en-nz', 'en-ng', 'en-pk', 'en-ph', 'en-sg', 'en-za', 'en-tz',
            'en-gb', 'en-us', 'et-ee', 'fil-ph', 'fi-fi', 'fr-be', 'fr-ca', 'fr-fr', 'fr-ch', 'gl-es', 'ka-ge', 'de-at',
            'de-de', 'de-ch', 'el-gr', 'gu-in', 'iw-il', 'hi-in', 'hu-hu', 'is-is', 'id-id', 'it-it', 'it-ch', 'ja-jp',
            'jv-id', 'kn-in', 'kk-kz', 'km-kh', 'ko-kr', 'lo-la', 'lv-lv', 'lt-lt', 'mk-mk', 'ms-my', 'ml-in', 'mr-in',
            'mn-mn', 'ne-np', 'no-no', 'fa-ir', 'pl-pl', 'pt-br', 'pt-pt', 'ro-ro', 'ru-ru', 'sr-rs', 'si-lk', 'sk-sk',
            'sl-si', 'es-ar', 'es-bo', 'es-cl', 'es-co', 'es-cr', 'es-do', 'es-ec', 'es-sv', 'es-gt', 'es-hn', 'es-mx',
            'es-ni', 'es-pa', 'es-py', 'es-pe', 'es-pr', 'es-es', 'es-us', 'es-uy', 'es-ve', 'su-id', 'sw-ke', 'sw-tz',
            'sv-se', 'ta-in', 'ta-my', 'ta-sg', 'ta-lk', 'te-in', 'th-th', 'tr-tr', 'uk-ua', 'ur-in', 'ur-pk', 'uz-uz',
            'vi-vn', 'zu-za', 'zh-tw (cmn-hant-tw)', 'zh (cmn-hans-cn)', 'yue-hant-hk', 'pa-guru-in'
        ]
        if (!languages.includes(language.toLowerCase())) {
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
        if (!text) {
            chat.sendMessage(
                'Burro burro! Você não inseriu nenhum texto! 🤦‍♂️',
                { sendSeen: true, quotedMessageId: data.id._serialized }
            );
            return;
        }

        const char_limit = 200;
        if (!text.length > char_limit) {
            await chat.sendMessage(
                await MessageMedia.fromUrl(audio_urls[0].url, { unsafeMime: true }),
                {
                    sendSeen: true,
                    isViewOnce: true,
                    sendAudioAsVoice: true,
                    quotedMessageId: data.id._serialized,
                }
            );
            return;
        }

        const audio_urls = tts.getAllAudioUrls(text, {
            lang: language,
            slow: false,
            host: 'https://translate.google.com',
            splitPunct: '.!?;:'
        });

        for (const audio_url of audio_urls) {
            await chat.sendMessage(
                await MessageMedia.fromUrl(audio_url.url, { unsafeMime: true }),
                {
                    sendSeen: true,
                    sendAudioAsVoice: true,
                    isViewOnce: true,
                    quotedMessageId: data.id._serialized,
                }
            );
        }
    }
}