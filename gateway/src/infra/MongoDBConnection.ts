import { MongoClient, Db, Collection, Document } from 'mongodb';

export default class MongoDBConnection {
  private static client: MongoClient | null = null;
  private static readonly DATABASE_NAME = 'resenhazord2';

  static async getClient(): Promise<MongoClient> {
    if (!this.client) {
      const uri = process.env.MONGODB_URI;
      if (!uri) throw new Error('MONGODB_URI environment variable is required');
      this.client = new MongoClient(uri);
      await this.client.connect();
    }
    return this.client;
  }

  static async getDatabase(): Promise<Db> {
    const client = await this.getClient();
    return client.db(this.DATABASE_NAME);
  }

  static async getCollection<T extends Document>(name: string): Promise<Collection<T>> {
    const db = await this.getDatabase();
    return db.collection<T>(name);
  }

  static async close(): Promise<void> {
    if (this.client) {
      await this.client.close();
      this.client = null;
    }
  }

  static isConnected(): boolean {
    return this.client !== null;
  }
}
