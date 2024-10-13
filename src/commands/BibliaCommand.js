import Resenhazord2 from "../models/Resenhazord2.js";
import axios from 'axios';

export default class BibliaCommand {

    static identifier = "^\\s*,\\s*b.blia\\s*(?:pt|en)?\\s*(?:nvi|ra|acf|kjv|bbe|apee|rvr)?\\s*(?:.*\\s*\\d{1,3}\\s*:\\s*\\d{1,3}\\s*(?:-\\s*\\d{1,3})?)?$";

    static async run(data) {

        const has_verse = data.text.match(/.+\s*\d{1,3}\s*:\s*\d{1,3}\s*(?:-\s*\d{1,3})?/);
        const lang = data.text.match(/\b(pt|en)\b/i) || 'pt';
        const version = data.text.match(/\b(nvi|ra|acf|kjv|bbe|apee|rvr)\b/i) || 'nvi';
        const token = process.env.BIBLIA_TOKEN;
        const headers = {
            Authorization: `Bearer ${token}`
        };

        const base_url = `https://www.abibliadigital.com.br/api`;
        let url;
        if (!has_verse) {
            url = `${base_url}/verses/${version}/random`;

            axios.get(url, { headers })
            .then(response => {
                this.send_verse(data, response.data);
            }).catch(error => {
                this.raise_generic_error(data,error);
            });
            return;
        }

        const rest_command = data.text.replace(/\s*,\s*b.blia\s*/, '')
                                .replace(/(pt|en)/, '')
                                .replace(/(nvi|ra|acf|kjv|bbe|apee|rvr)/, '')
                                .replace(/\d{1,3}\s*:\s*\d{1,3}\s*(?:-\s*\d{1,3})?/, '')
                                .trim();

        if (!rest_command || rest_command.match(/^\s*$/)){
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: 'Por favor, digite o nome do livro da bíblia... 😔'},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
            return;
        }

        const book = rest_command
        const chapter = data.text.match(/\d{1,3}:/)[0].replace(':', '');
        const has_range = data.text.match(/-\s*\d{1,3}/);
        const number = has_range ?
            data.text.match(/\d{1,3}\s*-\s*\d{1,3}/)[0].split('-').map(n => n.trim()) :
            data.text.match(/:\s*\d{1,3}/)[0].replace(':', '');

        let abbrev;
        await axios.get(`${base_url}/books`, { headers })
        .then(response => {
            const books = response.data;

            abbrev = books.find(b => b.name.toLowerCase() === book.toLowerCase())?.abbrev?.pt;
            if (!abbrev) {
                const book_names = books.map(b => `- ${b.name}`).join('\n');
                let text = 'Não consegui encontrar o livro que você digitou... 😔'
                text += '\n\n📚 *Livros Disponíveis* 📚\n';
                text += book_names;
                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {text: text},
                    {quoted: data, ephemeralExpiration: data.expiration}
                );
                return;
            }
        }).catch(error => {
            this.raise_generic_error(data, error);
        });

        if (!has_range) {
            url = `${base_url}/verses/${version}/${abbrev}/${chapter}/${number}`;

            axios.get(url, { headers })
            .then(response => {
                this.send_verse(data, response.data);
            }).catch(error => {
                this.raise_generic_error(data, error);
            });
            return;
        }
        const [start, end] = number;
        const verses = [];
        for (let i = parseInt(start); i <= parseInt(end); i++) {
            const verseUrl = `${base_url}/verses/${version}/${abbrev}/${chapter}/${i}`;
            try {
                const verseResponse = await axios.get(verseUrl, { headers });
                verses.push(`> ${verseResponse.data.text}`);
            } catch (error) {
                this.raise_generic_error(data, error);
                return;
            }
        }
        const text = `*${book} ${chapter}:${start}-${end}*\n\n${verses.join('\n')}`;
        Resenhazord2.socket.sendMessage(
            data.key.remoteJid,
            {text: text},
            {quoted: data, ephemeralExpiration: data.expiration}
        );
    }

    static async raise_generic_error(data, error) {
        console.log(`BIBLIA COMMAND ERROR\n${error}`);
        Resenhazord2.socket.sendMessage(
            data.key.remoteJid,
            {text: 'Perdoa-me Senhor, não consegui buscar o versículo... 😔'},
            {quoted: data, ephemeralExpiration: data.expiration}
        );
    }

    static async send_verse(data, verse) {
        Resenhazord2.socket.sendMessage(
            data.key.remoteJid,
            {text: `*${verse.book.name} ${verse.chapter}:${verse.number}*\n\n> ${verse.text}`},
            {quoted: data, ephemeralExpiration: data.expiration}
        );
    }
}