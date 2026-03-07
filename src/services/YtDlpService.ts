import { execFile } from 'child_process';
import { promisify } from 'util';

const execFileAsync = promisify(execFile);

export default class YtDlpService {
  static async download(url: string): Promise<{ buffer: Buffer; title: string }> {
    const { stdout: titleOut } = await execFileAsync('yt-dlp', ['--print', 'title', url]);
    const title = titleOut.trim() || 'Vídeo';

    const { stdout } = await execFileAsync(
      'yt-dlp',
      ['-f', 'best[ext=mp4]/best', '--max-filesize', '50m', '-o', '-', url],
      { encoding: 'buffer', maxBuffer: 100 * 1024 * 1024 },
    );

    return { buffer: Buffer.from(stdout), title };
  }
}
