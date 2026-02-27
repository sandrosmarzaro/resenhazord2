import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import Resenhazord2 from '../models/Resenhazord2.js';

export default class AdmCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*adm\\s*$';
  readonly menuDescription = 'Xingue aleatoriamente todos os administradores do grupo.';

  private readonly swearings = [
    'arrombado',
    'antisemita',
    'baba-ovo',
    'babaca',
    'baitola',
    'besta',
    'bluepill',
    'bicha',
    'buceta',
    'boco',
    'boiola',
    'boqueteiro',
    'cuzão',
    'bosta',
    'bostão',
    'punheteiro',
    'maluco',
    'broxa',
    'burro',
    'uma cadela',
    'cagão',
    'canalha',
    'uma xereca',
    'chifrudo',
    'cocô',
    'corno manso',
    'corno',
    'cornudo',
    'corrupto',
    'cretino',
    'cringe',
    'um cu',
    'cuzao',
    'debiloide',
    'demonio',
    'doido',
    'mongol',
    'escroto',
    'um resto de aborto',
    'adotado',
    'a vergonha da familia',
    'estupido',
    'fedido',
    'lixo',
    'feio',
    'feioso',
    'fudido',
    'furada',
    'gay',
    'gosmento',
    'homossexual',
    'idiota',
    'imbecil',
    'ladrao',
    'leproso',
    'monkey flip',
    'macaco',
    'animal',
    'anta',
    'merda',
    'merdinha',
    'merdona',
    'mijo',
    'moleque',
    'nojento',
    'otario',
    'paspalhao',
    'paspalho',
    'pentelho',
    'cancer',
    'um saco',
    'pilantra',
    'piranha',
    'um porra',
    'uma prostituta',
    'puxa-saco',
    'filha da puta',
    'crackudo',
    'integrante do stoneland',
    'biscate',
    'puxasaco',
    'lambe saco',
    'retardado',
    'ridículo',
    'torador de jumenta',
    'trouxa',
    'petista',
    'comunista',
    'nazista',
    'liberal',
    'neoliberal',
    'bolsonarista',
    'vagabundo',
    'peida xerequinha',
    'energúmeno',
    'igual seu pai de calcinha',
    'viado',
    'viadao',
    'shitpost',
    'baixista',
    'tchola',
    'feio igual um satanás',
    'falso',
    'maconheiro',
    'sapo feio da besta fera',
    'drogado',
    'usuário de crack',
    'ninguém',
    'oferenda pra iemanjá',
    'bobão',
    'youtuber',
    'tiktoker',
    'estrume',
    'escondido no armário',
    'horrível',
    'mamador do governo',
    'pau mandado',
  ];

  async run(data: CommandData): Promise<Message[]> {
    if (!data.key.remoteJid!.match(/g.us/)) {
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: `Burro burro! Você só pode xingar adminstração em um grupo! 🤦‍♂️` },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }

    const { participants } = await Resenhazord2.socket!.groupMetadata(data.key.remoteJid!);
    const adms = participants.filter((participant) => participant.admin);
    const adms_ids = adms.map((adm) => adm.id);
    const regex = /@lid|@s.whatsapp.net/gi;
    const adm_mentions = adms.map((adm) => `@${adm.id.replace(regex, '')} `);
    const random_swearing = this.swearings[Math.floor(Math.random() * this.swearings.length)];
    return [
      {
        jid: data.key.remoteJid!,
        content: {
          text: `Vai se foder administração! 🖕\nVocê é ${random_swearing}\n${adm_mentions.join('')}`,
          mentions: adms_ids,
        },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }
}
