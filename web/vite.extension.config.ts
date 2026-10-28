import { readFileSync } from "node:fs";
import { defineConfig } from "vite";

const ENTRIES = ["content", "background", "network", "wake"];
const ICON_SIZES = [16, 32, 48, 128];

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
          for (const size of ICON_SIZES) {
            const fileName = `icons/${size}.png`;
            this.emitFile({
              type: "asset",
              fileName,
              source: readFileSync(`extension/${fileName}`),
            });
          }
        },
      },
    ],
    build: {
      outDir: "../truapply/extension",
      emptyOutDir: entry === "content",
      minify: false,
      rollupOptions: {
        input: `extension/src/${entry}.ts`,
        output: { format: "iife", entryFileNames: `${entry}.js` },
      },
    },
  };
});
