import { vi } from 'vitest';

process.env.RESENHAZORD2_JID = '5500000000000@s.whatsapp.net';
process.env.MONGODB_URI = 'mongodb://localhost:27017/test';

vi.mock('google-tts-api', () => ({
  default: vi.fn().mockResolvedValue('mocked-audio-base64'),
}));

vi.mock('@google/generative-ai', () => ({
  GoogleGenerativeAI: vi.fn(() => ({
    getGenerativeModel: vi.fn(() => ({
      generateContent: vi.fn().mockResolvedValue({
        response: { text: () => 'Mocked AI response' },
      }),
    })),
  })),
}));

vi.mock('mongodb', () => {
  class MockMongoClient {
    connect = vi.fn().mockResolvedValue(undefined);
    db = vi.fn(() => ({
      collection: vi.fn(() => ({
        findOne: vi.fn().mockResolvedValue(null),
        insertOne: vi.fn().mockResolvedValue({ insertedId: 'test-id' }),
        updateOne: vi.fn().mockResolvedValue({ modifiedCount: 1 }),
        deleteOne: vi.fn().mockResolvedValue({ deletedCount: 1 }),
        find: vi.fn(() => ({
          toArray: vi.fn().mockResolvedValue([]),
        })),
      })),
    }));
    close = vi.fn().mockResolvedValue(undefined);
  }
  return { MongoClient: MockMongoClient };
});
