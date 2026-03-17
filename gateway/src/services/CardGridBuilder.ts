import sharp from 'sharp';

type CellBackground = string | { r?: number; g?: number; b?: number; alpha?: number };

export interface GridOptions {
  columns: number;
  cellWidth: number;
  cellHeight: number;
  shim: number;
  shimBackground: string;
  background: CellBackground;
}

export async function buildCardGrid(imageBuffers: Buffer[], opts: GridOptions): Promise<Buffer> {
  const resizedBuffers = await Promise.all(
    imageBuffers.map((buf) =>
      sharp(buf)
        .resize(opts.cellWidth, opts.cellHeight, { fit: 'contain', background: opts.background })
        .png()
        .toBuffer(),
    ),
  );

  return sharp(resizedBuffers, {
    join: { across: opts.columns, shim: opts.shim, background: opts.shimBackground },
  })
    .png()
    .toBuffer();
}
