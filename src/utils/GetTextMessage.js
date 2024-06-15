export default class GetTextMessage {

    static run(data) {
        return data.message?.conversation ||
                data.message?.extendedTextMessage?.text ||
                data.message?.videoMessage?.caption ||
                data.message?.imageMessage?.caption ||
                data.message?.documentWithCaptionMessage?.message?.documentMessage?.caption ||
                '';
    }
}