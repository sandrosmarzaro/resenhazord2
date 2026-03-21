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
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    fmt: (strings: TemplateStringsArray, ...values: unknown[]) =>
      String.raw({ raw: strings }, ...values),
  },
}));

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
