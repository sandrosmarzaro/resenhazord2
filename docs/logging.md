# Logging

Python uses `structlog` + `sentry-sdk` (FastApiIntegration). Gateway uses `@sentry/bun`. Production = JSON, dev = console.

## Python

`bot/infrastructure/logging.py` configures structlog. `bot/infrastructure/sentry.py` init with DSN (no DSN = no-op, safe for dev).

```python
logger = structlog.get_logger()
logger.info('event_name', key=value)
logger.exception('event_name', key=value)  # auto-captures traceback
```

### Error capture

```python
try:
    await risky_call()
except ExternalServiceError as exc:
    sentry_sdk.capture_exception(exc)
    logger.exception('failed', service='tmdb')
    raise
```

### Scoped context

```python
with sentry_sdk.push_scope() as scope:
    scope.set_tag('command', cmd.name)
    await cmd.run(data)
```

### Test mocks

```python
mocker.patch('sentry_sdk.capture_exception')
```

## Gateway (TypeScript)

```ts
import { Sentry } from './src/infra/Sentry.js';
Sentry.logger.info(Sentry.logger.fmt`event ${value}`);
Sentry.captureException(err, { extra: { chatJid } });
```

### Scoped context

```ts
Sentry.withScope((scope) => {
  scope.setTag('command', cmd.constructor.name);
  Sentry.captureException(err);
});
```

Test mocks in `gateway/tests/setup.ts` — `fmt` as tagged template literal.

## Sentry CLI

Install: `npm install -g @sentry/cli && sentry auth`

```bash
sentry issue list -p resenhazord2 -s unresolved  # list issues
sentry issue view <ID>                          # full details + stack trace
sentry issue explain <ID>                        # AI root cause
```

`handled=yes` = caught manually, `handled=no` = uncaught exception.