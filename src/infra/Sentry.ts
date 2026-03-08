import * as Sentry from '@sentry/bun';

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  tracesSampleRate: 0.1,
  _experiments: { enableLogs: true },
});

export { Sentry };
