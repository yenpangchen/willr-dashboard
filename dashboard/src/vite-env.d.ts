/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** API origin without trailing slash, e.g. https://api.example.com — omit when UI and API share the same host */
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
