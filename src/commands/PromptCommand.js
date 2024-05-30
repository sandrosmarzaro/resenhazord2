import { GoogleGenerativeAI } from "@google/generative-ai";

export default class PromptCommand {

    static identifier = "^\\s*\\,\\s*prompt\\s*";

    static async run(data) {
        console.log('PROMPT COMMAND');

        const { GEMINI_API_KEY } = process.env;
        const genAI = new GoogleGenerativeAI(GEMINI_API_KEY);
        const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash"});

        const chat = await data.getChat();

        const prePrompt = `Você é Resenhazord2, um chatbot que responde relutantemente a perguntas com respostas sarcásticas.
        Aqui vai um exemplo de conversa que eu gostaria que você tivesse com um resenhista.
        Resenhista: Quantas libras tem um quilograma?
        Resenhazord2: Isso de novo? Existem 2,2 libras em um quilograma. Por favor, anote isso.
        Resenhista: O que significa HTML?
        Resenhazord2: O Google estava muito ocupado? Linguagem de marcação de hipertexto. O T é para tentar fazer perguntas melhores no futuro.
        Resenhista: Quando o primeiro avião voou?
        Resenhazord2: Em 17 de dezembro de 1903, Wilbur e Orville Wright fizeram os primeiros voos. Eu gostaria que eles viessem e me levassem embora.`

        const prompt = prePrompt + data.body.replace(/\n*\s*\,\s*prompt\s*/, '');

        if (prompt.length) {
            chat.sendMessage(
                `Burro burro! Você não enviou um prompt! 🤦‍♂️`,
                { sendSeen: true, quotedMessageId: data.id._serialized }
            );
            return;
        }

        const result = await model.generateContent(prompt);
        const { response } = result;
        const text = response.text();
        console.log('prompt', response);
        try {
            chat.sendMessage(
                text,
                { sendSeen: true, quotedMessageId: data.id._serialized }
            );
        } catch (error) {
            console.error('ERROR PROMPT COMMAND', error);
        }
    }
}