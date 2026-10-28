import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const tracker = process.env.TRUAPPLY_TRACKER ?? "http://127.0.0.1:8765";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../truapply/tracker/static",
    emptyOutDir: true,
    modulePreload: { polyfill: false },
    assetsInlineLimit: 0,
  },
  server: {
    proxy: {
      "/api": { target: tracker, changeOrigin: true, headers: { Origin: tracker } },
      "^/jobs/\\d+/(screenshot\\.png|resume\\.pdf)$": { target: tracker, changeOrigin: true },
    },
  },
});
