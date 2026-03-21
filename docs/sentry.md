# Sentry Integration

`gateway/src/infra/Sentry.ts` initializes `@sentry/bun`. Always import as:

```ts
import { Sentry } from './src/infra/Sentry.js';
```

## Structured Logs

`Sentry.logger.<level>()` with `fmt` tagged template for interpolation:

```ts
Sentry.logger.warn(Sentry.logger.fmt`Cache miss for key ${key}: ${error}`);
```

Levels (low → high): `trace` · `debug` · `info` · `warn` · `error` · `fatal`

## Error Capture

Always include `extra` context to aid debugging:

```ts
Sentry.captureException(error, { extra: { method: 'create', chatJid } });
Sentry.captureMessage('Bot logged out', 'warning');
```

## Breadcrumbs

Trail of events before an error occurs:

```ts
Sentry.addBreadcrumb({ category: 'command', message: 'Executing FooCommand', level: 'info' });
```

## Scoped Context

Tag errors with structured metadata:

```ts
Sentry.withScope((scope) => {
  scope.setTag('command', command.constructor.name);
  scope.setExtra('jid', jid);
  Sentry.captureException(error);
});
```

## Traces

`tracesSampleRate: 0.1` (10%) configured in `Sentry.ts`; no manual spans currently.

## Sentry CLI

Uses `SENTRY_TOKEN` from `.env` for releases and source maps:

```bash
SENTRY_AUTH_TOKEN=$SENTRY_TOKEN sentry-cli releases ...
SENTRY_AUTH_TOKEN=$SENTRY_TOKEN sentry-cli sourcemaps upload ...
```

## Querying Issues

Use `SENTRY_TOKEN` from `.env` to query issues via the REST API without opening the web UI.

**List recent unresolved issues:**

```bash
curl -s \
  -H "Authorization: Bearer $SENTRY_TOKEN" \
  "https://sentry.io/api/0/projects/smarzaro/resenhazord2/issues/?query=is:unresolved&limit=10" \
  | python3 -c "import json,sys; [print(i['id'], i['shortId'], i['title']) for i in json.load(sys.stdin)]"
```

**Fetch a specific issue (title, culprit, tags):**

```bash
curl -s \
  -H "Authorization: Bearer $SENTRY_TOKEN" \
  "https://sentry.io/api/0/issues/<ISSUE_ID>/" \
  | python3 -m json.tool
```

**Get the latest event with full stack trace:**

```bash
curl -s \
  -H "Authorization: Bearer $SENTRY_TOKEN" \
  "https://sentry.io/api/0/issues/<ISSUE_ID>/events/latest/" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
for entry in d.get('entries', []):
    if entry.get('type') == 'exception':
        for exc in entry['data']['values']:
            print(exc.get('type'), exc.get('value'))
            for f in exc['stacktrace']['frames']:
                if f.get('inApp'):
                    print(f'  {f[\"filename\"]}:{f[\"lineNo\"]} in {f[\"function\"]}')
"
```

Replace `<ISSUE_ID>` with the numeric ID from the issue URL (e.g. `7333954839`) or use `shortId` like `RESENHAZORD2-9`.

## Test Mock

All Sentry APIs are mocked in `gateway/tests/setup.ts`. When adding new `Sentry.logger` usage, ensure `fmt` is mocked as a tagged template literal:

```ts
fmt: (strings: TemplateStringsArray, ...values: unknown[]) =>
  String.raw({ raw: strings }, ...values);
```
