import js from '@eslint/js';
import eslintConfigPrettier from 'eslint-config-prettier';

export default [
  { ...js.configs.recommended, files: ['**/*.js'] },
  {
    files: ['**/*.js'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: {
        process: 'readonly',
        console: 'readonly',
        Buffer: 'readonly',
        URL: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
      },
    },
    rules: {
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      'no-console': 'off',
      'no-lone-blocks': 'warn',
      'no-undef': 'error',
      'no-var': 'error',
      'prefer-const': 'warn',
    },
  },
  eslintConfigPrettier,
  {
    ignores: ['node_modules/**', 'auth_session/**', 'public/**', 'src/auth/session/**'],
  },
];
