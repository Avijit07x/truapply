import { readFileSync } from "node:fs";
import { defineConfig } from "vite";

const ENTRIES = ["content", "background", "network", "wake"];

export default defineConfig(({ mode }) => {
  const entry = ENTRIES.includes(mode) ? mode : "content";
  return {
    publicDir: false,
    plugins: [
      {
        name: "manifest",
        generateBundle() {
          if (entry !== "content") return;
          const source = readFileSync("extension/manifest.json", "utf-8");
          this.emitFile({ type: "asset", fileName: "manifest.json", source });
        },
      },
    ],
    build: {
      outDir: "../satyaapply/extension",
      emptyOutDir: entry === "content",
      minify: false,
      rollupOptions: {
        input: `extension/src/${entry}.ts`,
        output: { format: "iife", entryFileNames: `${entry}.js` },
      },
    },
  };
});
