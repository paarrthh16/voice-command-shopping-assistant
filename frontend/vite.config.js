import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// During development the frontend runs on :5173 and proxies /api to the
// FastAPI backend on :8000, so the browser only ever talks to one origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
