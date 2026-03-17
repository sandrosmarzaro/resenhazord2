import hitomi, { Extension, SortType, ThumbnailSize } from 'node-hitomi';
import AxiosClient from '../infra/AxiosClient.js';
import type { HentaiGallery, NhentaiGallery, NhentaiImage } from '../types/commands/hentai.js';

const NHENTAI_EXT_MAP: Record<NhentaiImage['t'], string> = {
  j: 'jpg',
  p: 'png',
  g: 'gif',
  w: 'webp',
};

export default class HentaiScraper {
  private static readonly MIRROR_URL = process.env.NHENTAI_MIRROR_URL ?? 'https://nhentai.net';
  private static readonly MAX_NHENTAI_ID = 500000;
  private static readonly NHENTAI_MAX_RETRIES = 5;

  static async getRandomGallery(): Promise<HentaiGallery> {
    try {
      return await HentaiScraper.fromHitomi();
    } catch {
      return await HentaiScraper.fromNhentai();
    }
  }

  private static readonly HITOMI_REFERER = 'https://hitomi.la/';

  static async fromHitomi(): Promise<HentaiGallery> {
    const refs = await hitomi.galleries.list({
      orderBy: SortType.Random,
      page: { index: 0, size: 25 },
    });

    const ref = refs[Math.floor(Math.random() * refs.length)];
    const gallery = await ref.retrieve();
    const rawCoverUrl = await gallery.files[0].resolveUrl(Extension.Webp, ThumbnailSize.Small);
    const coverUrl = rawCoverUrl.startsWith('//') ? `https:${rawCoverUrl}` : rawCoverUrl;

    return {
      title: gallery.title.display,
      japaneseTitle: gallery.title.japanese ?? undefined,
      artists: gallery.artists.map((a) => a.name),
      groups: gallery.groups.map((g) => g.name),
      tags: gallery.tags.map((t) => t.name),
      type: gallery.type,
      language: gallery.language?.name ?? 'unknown',
      pages: gallery.files.length,
      date: gallery.addedDate.toISOString().slice(0, 7),
      coverUrl,
      coverHeaders: { Referer: HentaiScraper.HITOMI_REFERER },
      url: `https://hitomi.la/galleries/${gallery.id}.html`,
    };
  }

  static async fromNhentai(): Promise<HentaiGallery> {
    for (let attempt = 0; attempt < HentaiScraper.NHENTAI_MAX_RETRIES; attempt++) {
      const id = Math.floor(Math.random() * HentaiScraper.MAX_NHENTAI_ID) + 1;

      try {
        const response = await AxiosClient.get<NhentaiGallery>(
          `${HentaiScraper.MIRROR_URL}/api/gallery/${id}`,
          { retries: 0 },
        );
        const g = response.data;

        const artists = g.tags.filter((t) => t.type === 'artist').map((t) => t.name);
        const groups = g.tags.filter((t) => t.type === 'group').map((t) => t.name);
        const tags = g.tags.filter((t) => t.type === 'tag').map((t) => t.name);
        const langTag = g.tags.find((t) => t.type === 'language');
        const typeTag = g.tags.find((t) => t.type === 'type');
        const coverExt = NHENTAI_EXT_MAP[g.images.cover.t] ?? 'jpg';
        const coverUrl = `https://t.nhentai.net/galleries/${g.media_id}/thumb.${coverExt}`;

        return {
          title: g.title.english || g.title.pretty,
          japaneseTitle: g.title.japanese || undefined,
          artists,
          groups,
          tags,
          type: typeTag?.name ?? 'manga',
          language: langTag?.name ?? 'unknown',
          pages: g.num_pages,
          date: new Date(g.upload_date * 1000).toISOString().slice(0, 7),
          coverUrl,
          url: `${HentaiScraper.MIRROR_URL}/g/${g.id}/`,
        };
      } catch (error: unknown) {
        const status = (error as { response?: { status: number } }).response?.status;
        if (status !== 404) throw error;
      }
    }

    throw new Error('Failed to fetch nhentai gallery after max retries');
  }
}
