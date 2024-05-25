export default class AdmCommand {
    static async run(data) {
        console.log('ADM COMMAND');

        const chat = await data.getChat(data);
        if (!chat.isGroup) {
            chat.sendMessage(
                `Burro burro! Você só pode xingar adminstração em um grupo! 🤦‍♂️`,
                { sendSeen: true, quotedMessageId: data.id._serialized }
            );
            return;
        }

        const swearings = [
            "arrombado", "antisemita", "baba-ovo", "babaca", "baitola", "besta", "bluepill", "bicha",
            "buceta", "boco", "boiola", "boqueteiro", "cuzão", "bosta", "bostão", "punheteiro", "maluco",
            "broxa", "burro", "uma cadela", "cagão", "canalha", "uma xereca", "chifrudo", "cocô", "corno manso",
            "corno", "cornudo", "corrupto", "cretino", "cringe", "um cu", "cuzao", "debiloide", "demonio", "doido",
            "mongol", "escroto", "um resto de aborto", "adotado", "a vergonha da familia", "estupido", "fedido",
            "lixo", "feio", "feioso", "fudido", "furada", "gay", "gosmento", "homossexual", "idiota", "imbecil",
            "ladrao", "leproso", "monkey flip", "macaco", "animal", "anta", "merda", "merdinha", "merdona", "mijo",
            "moleque", "nojento", "otario", "paspalhao", "paspalho", "pentelho", "cancer", "um saco", "pilantra",
            "piranha", "um porra", "uma prostituta", "puxa-saco", "filha da puta", "crackudo",
            "integrante do stoneland", "biscate", "puxasaco", "lambe saco", "retardado", "ridículo",
            "torador de jumenta", "trouxa", "petista", "comunista", "nazista", "liberal", "neoliberal",
            "bolsonarista", "vagabundo", "peida xerequinha", "energúmeno", "igual seu pai de calcinha", "viado",
            "viadao", "shitpost", "baixista", "tchola", "feio igual um satanás", "falso", "maconheiro",
            "sapo feio da besta fera", "drogado", "usuário de crack", "ninguém", "oferenda pra iemanjá", "bobão",
            "youtuber", "tiktoker", "estrume", "escondido no armário", "horrível", "mamador do governo",
            "pau mandado"
        ];

        const { participants } = chat;
        const adms = participants.filter(participant => participant.isAdmin);
        const adms_ids = adms.map(adm => adm.id._serialized);
        const adm_mentions = adms.map(adm => `@${adm.id.user} `);
        const random_swearing = swearings[Math.floor(Math.random() * swearings.length)];
        await chat.sendMessage(
            `Vai se foder administração! 🖕\nvocê é ${random_swearing}\n${adm_mentions.join('')} `,
            { sendSeen: true, quotedMessageId: data.id._serialized, mentions: adms_ids }
        );
    }
}