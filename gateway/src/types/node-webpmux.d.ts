declare module 'node-webpmux' {
  export class Image {
    exif: Buffer | null;
    load(buffer: Buffer): Promise<void>;
    save(path: string | null): Promise<Buffer>;
  }
}
