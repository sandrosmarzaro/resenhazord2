import Resenhazord2 from '../models/Resenhazord2.js';
import { NSFW } from 'nsfwhub';
import pkg from 'darksadas-yt-pornhub-scrape';
const { phdl } = pkg;

export default class PornoCommand {
  static identifier = '^\\s*\\,\\s*porno\\s*(?:ia)?\\s*(?:show)?\\s*(?:dm)?$';

  static async run(data) {
    const ia_activate = data.text.match(/ia/);
    try {
      if (ia_activate) {
        await this.ia_porn(data);
        return;
      }
      await this.real_porn(data);
    } catch (error) {
      console.log(`ERROR PORN COMMAND\n${error}`);
      await Resenhazord2.socket.sendMessage(
        data.key.remoteJid,
        { text: 'Não consegui baixar seu vídeo, vai ter que ficar molhadinho 🥶' },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
    }
  }

  static async ia_porn(data) {
    const nsfw = new NSFW();
    const tags = [
      'ass',
      'sixtynine',
      'pussy',
      'dick',
      'anal',
      'boobs',
      'bdsm',
      'black',
      'easter',
      'bottomless',
      'blowjub',
      'collared',
      'cum',
      'cumsluts',
      'dp',
      'dom',
      'extreme',
      'feet',
      'finger',
      'fuck',
      'futa',
      'gay',
      'gif',
      'group',
      'hentai',
      'kiss',
      'lesbian',
      'lick',
      'pegged',
      'phgif',
      'puffies',
      'real',
      'suck',
      'tattoo',
      'tiny',
      'toys',
      'xmas',
    ];
    const tag = tags[Math.floor(Math.random() * tags.length)];
    const porn = await nsfw.fetch(tag);
    const content = {
      viewOnce: !data.text.match(/show/),
      caption: 'Aqui está seu vídeo 🤤',
    };

    if (porn?.image?.url?.endsWith('.mp4')) {
      content.video = { url: porn.image.url };
    } else if (porn?.image?.url?.endsWith('.gif')) {
      content.image = { url: porn.image.url };
      content.gifPlayback = true;
    } else {
      content.image = { url: porn.image.url };
    }

    let chat_id = data.key.remoteJid;
    const DM_FLAG_ACTIVE = data.text.match(/dm/);
    if (DM_FLAG_ACTIVE && data.key.participant) {
      chat_id = data.key.participant;
    }
    await Resenhazord2.socket.sendMessage(chat_id, content, {
      quoted: data,
      ephemeralExpiration: data.expiration,
    });
  }

  static async real_porn(data) {
    await phdl('https://pt.pornhub.com/random')
      .then(async (results) => {
        let chat_id = data.key.remoteJid;
        const DM_FLAG_ACTIVE = data.text.match(/dm/);
        if (DM_FLAG_ACTIVE && data.key.participant) {
          chat_id = data.key.participant;
        }
        await Resenhazord2.socket.sendMessage(
          chat_id,
          {
            video: {
              url: results.format[0].download_url,
            },
            caption: results.video_title,
            viewOnce: !data.text.match(/show/),
          },
          { quoted: data, ephemeralExpiration: data.expiration },
        );
      })
      .catch(async (error) => {
        console.log(`ERROR PORN COMMAND\n${error}`);
        await Resenhazord2.socket.sendMessage(
          data.key.remoteJid,
          { text: 'Não consegui baixar seu vídeo, vai ter que ficar molhadinho 🥶' },
          { quoted: data, ephemeralExpiration: data.expiration },
        );
      });
  }
}
