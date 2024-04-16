import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  server: { port: 7242, strictPort: true },
  preview: { port: 7242, strictPort: true },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.js'],
  },
});
