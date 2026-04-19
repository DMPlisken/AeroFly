import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// Inside docker-compose, the gateway is reachable at `http://gateway:8000`.
// Outside docker, override VITE_DEV_API_PROXY (e.g. `http://localhost:18000`).
const DEV_API_PROXY =
  process.env.VITE_DEV_API_PROXY ?? "http://gateway:8000";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3000,
    host: true,
    proxy: {
      "/api": {
        target: DEV_API_PROXY,
        changeOrigin: true,
      },
    },
  },
});
