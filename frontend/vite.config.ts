import { ServerResponse } from 'node:http'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'
import { API_PATH_PATTERN, normalizeBasePath } from './vite.helpers.ts'

const API_TARGET = 'http://localhost:8000'
const UPSTREAM_UNAVAILABLE = JSON.stringify({ detail: `Upstream API unavailable at ${API_TARGET}` })

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => {
  // VITE_BASE_PATH (build only): public base path for static hosting such as
  // GitHub Pages, e.g. VITE_BASE_PATH=drainfast -> assets served from /drainfast/.
  // Normalized to exactly one leading and one trailing '/'; unset or blank -> '/'.
  // Read from .env* files via loadEnv, with process.env taking precedence.
  // The dev server (`vite` / `npm run dev`) always uses '/'.
  const env = { ...loadEnv(mode, process.cwd(), 'VITE_'), ...process.env }

  return {
    plugins: [react()],
    base: command === 'build' ? normalizeBasePath(env.VITE_BASE_PATH) : '/',
    server: {
      port: 5173,
      strictPort: true,
      proxy: {
        // Backend API paths only; path and query are forwarded unchanged (no rewrite).
        [API_PATH_PATTERN]: {
          target: API_TARGET,
          changeOrigin: false, // keep Host and other request headers as sent
          timeout: 30_000,
          proxyTimeout: 30_000,
          configure: (proxy) => {
            // Registered before Vite's own handler, so this 502 wins when the API is down.
            proxy.on('error', (_err, _req, res) => {
              try {
                if (res instanceof ServerResponse) {
                  if (!res.headersSent && !res.writableEnded) {
                    res.writeHead(502, { 'Content-Type': 'application/json' })
                    res.end(UPSTREAM_UNAVAILABLE)
                  }
                } else if (!res.destroyed) {
                  // WebSocket/upgrade socket: nothing to respond with, just close it.
                  res.destroy()
                }
              } catch {
                // Never throw from the proxy error handler; keep the dev server alive.
              }
            })
          },
        },
      },
    },
  }
})
