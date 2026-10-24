/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Optional absolute API base URL. Blank -> relative URLs on the page's origin. */
  readonly VITE_API_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
