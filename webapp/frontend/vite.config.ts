import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Builds straight into webapp/static/, which FastAPI already serves at
// "/" (index.html) and "/static" (everything else, including the hashed
// assets/ output) - see webapp/server.py. base must match that mount path
// so the built index.html references /static/assets/... correctly.
export default defineConfig({
  plugins: [react()],
  base: '/static/',
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/ws': { target: 'ws://127.0.0.1:8000', ws: true },
      '/video_feed': 'http://127.0.0.1:8000',
      '/snapshots': 'http://127.0.0.1:8000',
    },
  },
  build: {
    outDir: '../static',
    emptyOutDir: true,
  },
})
