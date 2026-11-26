import { init, consoleLoggingIntegration } from '@sentry/bun';

init({
  dsn: process.env.SENTRY_DSN,
  // handleUnhandledRejection is the only capture: the SDK's would also send the 1006 it filters
  integrations: (defaults) => [
    ...defaults.filter((integration) => integration.name !== 'OnUnhandledRejection'),
    consoleLoggingIntegration({ levels: ['log', 'warn', 'error'] }),
  ],
  tracesSampleRate: 0.1,
  enableLogs: true,
});

export * as Sentry from '@sentry/bun';
