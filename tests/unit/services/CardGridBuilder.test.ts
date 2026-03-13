import { describe, it, expect, vi, beforeEach } from 'vitest';
import sharp from 'sharp';
import { buildCardGrid } from '../../../src/services/CardGridBuilder.js';

const mockSharp = sharp as unknown as ReturnType<typeof vi.fn>;

const baseOpts = {
  columns: 3,
  cellWidth: 300,
  cellHeight: 420,
  shim: 0,
  shimBackground: '#ffffff',
  background: '#ffffff',
};

describe('buildCardGrid', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should return a Buffer', async () => {
    const buffers = [Buffer.from('a'), Buffer.from('b'), Buffer.from('c')];

    const result = await buildCardGrid(buffers, baseOpts);

    expect(Buffer.isBuffer(result)).toBe(true);
  });

  it('should call sharp once per image for resizing, then once for the grid join', async () => {
    const buffers = [Buffer.from('a'), Buffer.from('b'), Buffer.from('c')];

    await buildCardGrid(buffers, baseOpts);

    expect(mockSharp).toHaveBeenCalledTimes(4); // 3 resizes + 1 join
  });

  it('should resize each image to the specified cell dimensions', async () => {
    const buffers = [Buffer.from('a')];
    const opts = { ...baseOpts, cellWidth: 475, cellHeight: 475 };

    await buildCardGrid(buffers, opts);

    const sharpInstance = mockSharp.mock.results[0].value;
    expect(sharpInstance.resize).toHaveBeenCalledWith(
      475,
      475,
      expect.objectContaining({ fit: 'contain' }),
    );
  });

  it('should pass the background to the cell resize call', async () => {
    const buffers = [Buffer.from('a')];
    const bg = { r: 0, g: 0, b: 0, alpha: 0 };
    const opts = { ...baseOpts, background: bg };

    await buildCardGrid(buffers, opts);

    const sharpInstance = mockSharp.mock.results[0].value;
    expect(sharpInstance.resize).toHaveBeenCalledWith(
      expect.any(Number),
      expect.any(Number),
      expect.objectContaining({ background: bg }),
    );
  });

  it('should join with the specified columns and shim', async () => {
    const buffers = [Buffer.from('a'), Buffer.from('b'), Buffer.from('c')];
    const opts = { ...baseOpts, columns: 3, shim: 8, shimBackground: '#000000' };

    await buildCardGrid(buffers, opts);

    expect(mockSharp).toHaveBeenLastCalledWith(
      expect.any(Array),
      expect.objectContaining({
        join: expect.objectContaining({ across: 3, shim: 8, background: '#000000' }),
      }),
    );
  });
});
