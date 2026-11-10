import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['tests/**/*.test.ts'],
    setupFiles: ['tests/setup.ts'],
    coverage: {
      provider: 'v8',
      // Repo-root paths (gateway/src/...) so diff-cover matches git diff paths. lcov
      // feeds Codecov and Sonar; diff-cover reads cobertura, because its lcov parser
      // ignores --branch-coverage and lets partial branches through.
      reporter: ['text', ['lcov', { projectRoot: '..' }], ['cobertura', { projectRoot: '..' }]],
      include: ['src/**/*.ts'],
      exclude: ['src/types/**/*.d.ts', 'src/scripts/**/*.ts'],
    },
  },
});
