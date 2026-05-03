# Logging

Python core uses `structlog` for structured logs and `sentry-sdk` (with
`FastApiIntegration`) for error capture. The Gateway uses `@sentry/bun` for both.
Production logs are JSON; local development uses the console renderer.

## Python

### Initialization

`bot/infrastructure/logging.py` routes all logs (including uvicorn) through
structlog. `configure_logging()` runs at FastAPI startup.

```python
import structlog

logger = structlog.get_logger()
```

`bot/infrastructure/sentry.py` initializes `sentry_sdk` with the FastAPI
integration. Unhandled exceptions inside request handlers are captured automatically;
you only call `capture_exception` for errors you catch and handle.

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

def init_sentry(dsn: str | None = None) -> None:
    if dsn:
        sentry_sdk.init(
            dsn=dsn,
            traces_sample_rate=0.1,
            integrations=[FastApiIntegration()],
        )
```

Absent DSN = all Sentry calls are no-ops (safe for local dev).

### Structured logging

Every log is an event name plus key/value context. No interpolated strings.

```python
logger.debug('handle_parsed', repeat=repeat, text=repr(data.text))
logger.info('discord_command_registered', name=command.config.name)
logger.warning('discord_image_download_failed', url=content.url)
logger.exception('command_execution_failed', command=command_name)
```

- `logger.exception(event)` captures the current traceback automatically.
- Use snake_case event names; make them greppable.
- Never interpolate into the event name: `logger.info(f'got {n}')` breaks search.

### Error capture

`FastApiIntegration` auto-captures unhandled request exceptions. For explicit
capture in non-request paths (background tasks, Discord handlers):

```python
import sentry_sdk

try:
    await risky_call()
except ExternalServiceError as exc:
    sentry_sdk.capture_exception(exc)
    logger.exception('external_service_failed', service='tmdb')
    raise
```

### Scoped context

Attach command metadata to everything captured inside the block:

```python
with sentry_sdk.push_scope() as scope:
    scope.set_tag('command', command.config.name)
    scope.set_context('parsed', {'flags': list(parsed.flags), 'rest': parsed.rest})
    await command.run(data)
```

### Breadcrumbs

Trail of events before an error:

```python
sentry_sdk.add_breadcrumb(
    category='command',
    message='executing_command',
    data={'name': command.config.name},
    level='info',
)
```

### Test mocks

Use `pytest-mock`'s `mocker` fixture to stub `sentry_sdk` calls:

```python
def test_command_captures_error(mocker):
    capture = mocker.patch('sentry_sdk.capture_exception')

    ...  # trigger the error path

    capture.assert_called_once()
```

Do not import from `unittest.mock` directly.

## Gateway (TypeScript)

`gateway/src/infra/Sentry.ts` initializes `@sentry/bun`. Always import as:

```ts
import { Sentry } from './src/infra/Sentry.js';
```

### Structured logs

`Sentry.logger.<level>()` with the `fmt` tagged template for interpolation:

```ts
Sentry.logger.warn(Sentry.logger.fmt`Cache miss for key ${key}: ${error}`);
```

Levels (low → high): `trace` · `debug` · `info` · `warn` · `error` · `fatal`.

### Error capture

Always include `extra` context:

```ts
Sentry.captureException(error, { extra: { method: 'create', chatJid } });
Sentry.captureMessage('Bot logged out', 'warning');
```

### Breadcrumbs

```ts
Sentry.addBreadcrumb({
  category: 'command',
  message: 'Executing FooCommand',
  level: 'info',
});
```

### Scoped context

Tag errors with structured metadata:

```ts
Sentry.withScope((scope) => {
  scope.setTag('command', command.constructor.name);
  scope.setExtra('jid', jid);
  Sentry.captureException(error);
});
```

### Traces

`tracesSampleRate: 0.1` (10 %) configured in `Sentry.ts`; no manual spans currently.

### Test mocks

All Sentry APIs are mocked in `gateway/tests/setup.ts`. When adding new
`Sentry.logger` usage, ensure `fmt` is mocked as a tagged template literal:

```ts
fmt: (strings: TemplateStringsArray, ...values: unknown[]) =>
  String.raw({ raw: strings }, ...values);
```

## CLI

Use `SENTRY_TOKEN` from `.env` for releases and source maps:

```bash
SENTRY_AUTH_TOKEN=$SENTRY_TOKEN sentry-cli releases ...
SENTRY_AUTH_TOKEN=$SENTRY_TOKEN sentry-cli sourcemaps upload ...
```

### Query issues without opening the web UI

List recent unresolved issues:

```bash
curl -s \
  -H "Authorization: Bearer $SENTRY_TOKEN" \
  "https://sentry.io/api/0/projects/smarzaro/resenhazord2/issues/?query=is:unresolved&limit=10" \
  | python3 -c "import json,sys; [print(i['id'], i['shortId'], i['title']) for i in json.load(sys.stdin)]"
```

Fetch a specific issue:

```bash
curl -s \
  -H "Authorization: Bearer $SENTRY_TOKEN" \
  "https://sentry.io/api/0/issues/<ISSUE_ID>/" \
  | python3 -m json.tool
```

Get the latest event with full stack trace:

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

Replace `<ISSUE_ID>` with the numeric ID or `shortId` (e.g., `RESENHAZORD2-9`).
