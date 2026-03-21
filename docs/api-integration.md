# External API Integration

1. **Test APIs first** — curl endpoints before implementing to check response format, latency, and payload size
2. **Read API docs fully** — look for simpler endpoints (e.g., `/random/card` instead of multi-step fetch), recommended formats (webp vs png), and asset URL construction rules
3. **Pre-download media as buffers** — use `AxiosClient.getBuffer()` + `Reply.to(data).imageBuffer()` so download errors are caught inside the command's try-catch, not in `sendMessages()` which only has the generic CommandHandler error handler
4. **Disable retries for slow APIs** — pass `retries: 0` in config; default 3 retries with exponential backoff silently multiply latency
5. **Prefer small formats** — use webp over png for images (can be 10x+ smaller); check API docs for recommended formats
6. **Set realistic timeouts** — consider production server latency, not local; production servers may have higher latency to external APIs
7. **Test media/asset URLs with curl — not just the API endpoint** — APIs often return
   asset URLs (images, audio) served by a CDN that requires extra headers the API call
   does not. Test the asset URL directly with and without `Referer`, `Origin`, and
   `Authorization` headers. CDNs commonly require `Referer` to the source site
   (e.g., `Referer: https://hitomi.la/` for hitomi CDN). A 404 on the asset after a
   successful API response is the signature of a missing header.

   ```bash
   # Without headers (will 404 on many CDNs):
   curl -I "<asset-url>"
   # With Referer:
   curl -I -H "Referer: https://example.com/" "<asset-url>"
   ```

8. **Verify fallback sources independently** — if a scraper has a primary + fallback
   path (try A, catch → try B), test B in isolation _before_ shipping. A broken fallback
   that swallows all errors and exhausts retries is worse than no fallback: it silently
   delays the real error. If the fallback source is known-broken (e.g. nhentai.xxx API),
   either remove it or gate it behind a guard that throws immediately.
