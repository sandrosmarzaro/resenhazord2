import tseslint from 'typescript-eslint';
import eslintConfigPrettier from 'eslint-config-prettier';

export default tseslint.config(
  ...tseslint.configs.recommended,
  {
    files: ['**/*.ts'],
    rules: {
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/no-explicit-any': 'warn',
      'no-console': 'off',
    },
  },
  eslintConfigPrettier,
  {
    ignores: [
      'node_modules/**',
      'auth_session/**',
      'public/**',
      'src/auth/session/**',
      'coverage/**',
    ],
  },
);
