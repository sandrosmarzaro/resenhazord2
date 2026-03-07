import { vi } from 'vitest';
import type WhatsAppPort from '../../../src/ports/WhatsAppPort.js';

export function createMockWhatsAppPort(overrides: Partial<WhatsAppPort> = {}): WhatsAppPort {
  return {
    sendMessage: vi.fn(),
    groupMetadata: vi.fn(),
    groupParticipantsUpdate: vi.fn(),
    groupUpdateSubject: vi.fn(),
    groupUpdateDescription: vi.fn(),
    updateProfilePicture: vi.fn(),
    onWhatsApp: vi.fn(),
    updateMediaMessage: vi.fn(),
    ...overrides,
  } as WhatsAppPort;
}
