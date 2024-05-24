import qrcode from 'qrcode-terminal'

export default class CreateQRCode {

    static run(qr) {
        qrcode.generate(qr, {small: true});
    }
}