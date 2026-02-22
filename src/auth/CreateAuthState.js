import { MongoClient } from 'mongodb';
import { useMongoDBAuthState } from './MongoDBAuthState.js';

export default class CreateAuthState {
    static async getAuthState() {
        const client = new MongoClient(process.env.MONGODB_URI);
        await client.connect();
        const collection = client.db('resenhazord2').collection('auth_state');
        return useMongoDBAuthState(collection);
    }
}
