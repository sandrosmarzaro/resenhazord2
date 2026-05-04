import { init, consoleLoggingIntegration } from '@sentry/bun';

init({
  dsn: process.env.SENTRY_DSN,
  integrations: [consoleLoggingIntegration({ levels: ['log', 'warn', 'error'] })],
  tracesSampleRate: 0.1,
  enableLogs: true,
});

export * as Sentry from '@sentry/bun';
