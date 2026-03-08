import { vi } from 'vitest';

process.env.RESENHAZORD2_JID = '5500000000000@s.whatsapp.net';
process.env.MONGODB_URI = 'mongodb://localhost:27017/test';

vi.mock('@sentry/bun', () => ({
  init: vi.fn(),
  captureException: vi.fn(),
  captureMessage: vi.fn(),
  withScope: vi.fn((cb: (scope: unknown) => void) => cb({ setTag: vi.fn(), setExtra: vi.fn() })),
  addBreadcrumb: vi.fn(),
  consoleLoggingIntegration: vi.fn(() => ({})),
  logger: {
    warn: vi.fn(),
    fmt: (strings: TemplateStringsArray, ...values: unknown[]) =>
      String.raw({ raw: strings }, ...values),
  },
}));

vi.mock('google-tts-api', () => {
  const tts = vi.fn().mockResolvedValue('mocked-audio-base64');
  (tts as unknown as Record<string, unknown>).getAllAudioUrls = vi
    .fn()
    .mockReturnValue([{ url: 'https://translate.google.com/translate_tts?q=mocked&tl=pt-br' }]);
  return { default: tts };
});

vi.mock('@google/generative-ai', () => {
  class MockGoogleGenerativeAI {
    getGenerativeModel = vi.fn(() => ({
      generateContent: vi.fn().mockResolvedValue({
        response: { text: () => 'Mocked AI response' },
      }),
    }));
  }
  return { GoogleGenerativeAI: MockGoogleGenerativeAI };
});

vi.mock('nsfwhub', () => {
  class MockNSFW {
    fetch = vi.fn().mockResolvedValue({
      image: { url: 'https://example.com/nsfw.mp4' },
    });
  }
  return { NSFW: MockNSFW };
});

vi.mock('sharp', () => {
  const sharpInstance = {
    resize: vi.fn().mockReturnThis(),
    png: vi.fn().mockReturnThis(),
    toBuffer: vi.fn().mockResolvedValue(Buffer.from('mock-image')),
  };
  const sharpFn = vi.fn().mockReturnValue(sharpInstance);
  return { default: sharpFn };
});

vi.mock('pino', () => ({
  default: vi.fn(() => ({ level: 'silent' })),
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
