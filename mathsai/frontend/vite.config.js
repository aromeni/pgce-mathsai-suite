import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxies /api to the FastAPI backend during development so the client can
// use relative paths (same-origin) — this sidesteps browser CORS entirely
// rather than configuring CORS on the backend, which CLAUDE.md scopes to
// Phase 8 (deployment). The same relative-path client code also works
// unchanged once both are served from one origin in production.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
