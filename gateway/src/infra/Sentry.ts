import * as Sentry from '@sentry/bun';

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  integrations: [Sentry.consoleLoggingIntegration({ levels: ['log', 'warn', 'error'] })],
  tracesSampleRate: 0.1,
  enableLogs: true,
});

export { Sentry };
