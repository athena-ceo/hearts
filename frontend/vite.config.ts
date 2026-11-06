// Copyright (c) 2026 Athena Decisions Systems SAS.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Base path: "/" in dev, "/hearts/" in production (behind nginx).
export default defineConfig({
  base: process.env.VITE_BASE_PATH ?? "/",
  plugins: [react()],
  server: {
    port: 3050,
    proxy: { "/api": { target: "http://localhost:8050", ws: true } },
  },
});
