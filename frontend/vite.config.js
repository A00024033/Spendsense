import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development, /api calls are forwarded to the FastAPI backend.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    proxy: { "/api": process.env.API_URL || "http://localhost:8000" },
  },
});
