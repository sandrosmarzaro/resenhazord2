import { MongoClient } from 'mongodb';

export default class BorgesCommand {

    static identifier = "^\\s*\\,\\s*borges\\s*$";

    static async run(data) {

        const uri = process.env.MONGODB_URI;
        const client = new MongoClient(uri);
        const chat = await data.getChat();
        try {
            await client.connect();
            const database = client.db('resenhazord2');
            const collection = database.collection('borges');
            const result = await collection.findOneAndUpdate(
                { _id: 'counter' },
                { $inc: { nargas: 1 } },
                { returnDocument: 'after', upsert: true }
            );
            console.log('borges', result);
            chat.sendMessage(
                `Borges já fumou ${result.nargas} nargas 🚬`,
                { sendSeen: true, quotedMessageId: data.id._serialized }
            );
        }
        catch (error) {
            console.error('BORGES COMMAND ERROR', error);
            chat.sendMessage(
                'Eram muitas bitucas para contar e não consegui... 😔',
                { sendSeen: true, quotedMessageId: data.id._serialized }
            );
        }
        finally {
            await client.close();
        }
    }
}