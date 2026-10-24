import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// Standalone test config: kept separate from vite.config.ts so tests do not
// depend on dev-server env (base path, proxy). tests/ is intentionally outside
// the tsc -b project includes; vitest type-strips test files itself.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    include: ['tests/**/*.test.ts', 'tests/**/*.test.tsx'],
    passWithNoTests: true,
  },
})
