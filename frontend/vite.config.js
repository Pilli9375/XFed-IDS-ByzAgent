import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Backend (backend/main.py) has no CORS middleware and is not to be
// modified here -- proxying /api/* to it server-side sidesteps CORS
// entirely instead of needing an allow_origins change.
// `preview` (the production-build static server, used to test the real
// dist/ bundle) does NOT inherit `server.proxy` -- it has its own separate
// option. Duplicated rather than shared because vite's config typing wants
// each block's shape explicit; keep both in sync if the target ever changes.
const apiProxy = {
  '/api': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, ''),
  },
}

export default defineConfig({
  plugins: [react()],
  server: { proxy: apiProxy },
  preview: { proxy: apiProxy },
})
