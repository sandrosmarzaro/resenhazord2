import MongoDBConnection from '../infra/MongoDBConnection.js';
import { useMongoDBAuthState, type MongoDBAuthResult } from './MongoDBAuthState.js';

export default class CreateAuthState {
  static async getAuthState(): Promise<MongoDBAuthResult> {
    const collection = await MongoDBConnection.getCollection('auth_state');
    return useMongoDBAuthState(collection);
  }
}
