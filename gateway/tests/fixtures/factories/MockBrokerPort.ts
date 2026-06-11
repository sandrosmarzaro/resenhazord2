import { vi } from 'vitest';
import type BrokerPort from '../../../src/ports/BrokerPort.js';

export function createMockBrokerPort(overrides: Partial<BrokerPort> = {}): BrokerPort {
  return {
    connect: vi.fn(),
    publish: vi.fn().mockResolvedValue(undefined),
    consume: vi.fn().mockResolvedValue(undefined),
    respondRpc: vi.fn().mockResolvedValue(undefined),
    close: vi.fn(),
    ...overrides,
  };
}
