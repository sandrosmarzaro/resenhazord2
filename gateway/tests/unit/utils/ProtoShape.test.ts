import { describe, it, expect } from 'vitest';
import ProtoShape from '../../../src/utils/ProtoShape.js';

describe('ProtoShape', () => {
  it('lists the paths of set fields without their values', () => {
    const message = {
      viewOnceMessageV2: { message: { imageMessage: { mimetype: 'image/jpeg', caption: 'oi' } } },
    };

    expect(ProtoShape.paths(message)).toEqual([
      'viewOnceMessageV2.message.imageMessage.mimetype',
      'viewOnceMessageV2.message.imageMessage.caption',
    ]);
  });

  it('skips unset fields', () => {
    const message = { imageMessage: { url: '', directPath: null, mediaKey: undefined, height: 0 } };

    expect(ProtoShape.paths(message)).toEqual(['imageMessage.height']);
  });

  it('treats byte arrays as leaves', () => {
    const message = { imageMessage: { mediaKey: new Uint8Array([1, 2, 3]) } };

    expect(ProtoShape.paths(message)).toEqual(['imageMessage.mediaKey']);
  });

  it('stops descending at the depth limit', () => {
    const message = { a: { b: { c: { d: { e: 'deep' } } } } };

    expect(ProtoShape.paths(message)).toEqual(['a.b.c.d']);
  });

  it('returns no paths for a missing message', () => {
    expect(ProtoShape.paths(null)).toEqual([]);
  });
});
