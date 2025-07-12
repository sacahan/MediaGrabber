import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
// import autoprefixer from 'autoprefixer';

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte()],
  css: {
    postcss: {
      plugins: [
        // autoprefixer,
        // Tailwind CSS 應該由 postcss.config.js 自動處理
      ],
    },
  },
});
