import pino from 'pino';

const logger = pino({
  level: process.env.LOG_LEVEL ?? 'info',
  timestamp: pino.stdTimeFunctions.isoTime,
  base: null,
  formatters: {
    level: (label) => ({ level: label }),
  },
});

export default logger;
