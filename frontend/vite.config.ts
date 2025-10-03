import { defineConfig } from "vite";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": resolve(dirname(fileURLToPath(import.meta.url)), "src"),
      "@/api": resolve(dirname(fileURLToPath(import.meta.url)), "src/lib/api"),
    },
  },
  server: {
    host: '127.0.0.1', // bind only to loopback (no LAN/virtual links)
    port: 5173,
    strictPort: true,
    open: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
      },
    },
  },
});