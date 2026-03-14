export interface WikiPage {
  title?: string;
  thumbnail?: { source: string };
}

export interface WikiQueryResponse {
  query?: { pages?: Record<string, WikiPage> };
}

export interface WikipediaSummaryResponse {
  extract: string;
  thumbnail?: { source: string };
}
