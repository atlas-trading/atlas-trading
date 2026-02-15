import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
  },
  resolve: {
    alias: {
      'react-is': 'react-is',
    },
  },
  optimizeDeps: {
    include: ['react-is', 'recharts'],
  },
});
