import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The browser only ever calls same-origin "/api/..." URLs (see src/services/api.ts).
// In development Vite proxies them to the backend — server-side, so this works on any host
// (preview URLs, LAN, Docker), not just when the browser runs on the backend's machine.
// Override the backend address with VITE_API_PROXY, e.g. http://backend:8000 inside Docker Compose.
const apiProxy = process.env.VITE_API_PROXY ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    allowedHosts: true,
    proxy: {
      // xfwd: send X-Forwarded-For so the backend rate limiter sees each browser, not 127.0.0.1.
      "/api": { target: apiProxy, changeOrigin: true, xfwd: true },
    },
  },
  preview: {
    host: "0.0.0.0",
    port: 4173,
    allowedHosts: true,
    proxy: {
      "/api": { target: apiProxy, changeOrigin: true, xfwd: true },
    },
  },
});
