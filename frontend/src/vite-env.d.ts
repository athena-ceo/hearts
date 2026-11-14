// Copyright (c) 2026 Athena Decision Systems SAS.
/// <reference types="vite/client" />
interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
  readonly VITE_BASE_PATH?: string;
}
interface ImportMeta { readonly env: ImportMetaEnv; }
