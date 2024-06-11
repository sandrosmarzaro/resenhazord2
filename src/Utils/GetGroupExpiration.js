import Resenhazord2 from "../models/Resenhazord2.js";

export default class GetGroupExpiration {

    static async run(data) {
        return data.message?.extendedTextMessage?.contextInfo?.expiration ||
                data.message?.imageMessage?.contextInfo?.expiration ||
                data.message?.videoMessage?.contextInfo?.expiration ||
                data.message?.documentWithCaptionMessage?.message?.documentMessage?.contextInfo?.expiration ||
                await Resenhazord2.socket.groupMetadata?.ephemeralDuration;
    }
}