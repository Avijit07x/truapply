import { QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./app/App";
import { queryClient } from "./app/queryClient";
import { preload } from "./app/routes";
import { syncTheme } from "./app/theme";
import { RouterProvider } from "./lib/router";
import "./styles/base.css";

const FIRST_PAINT_WAIT_MS = 300;

function shortly(ms: number): Promise<void> {
  return new Promise((done) => {
    setTimeout(done, ms);
  });
}

const root = document.getElementById("root");
syncTheme();
if (root) {
  await Promise.race([preload(window.location.href), shortly(FIRST_PAINT_WAIT_MS)]);
  createRoot(root).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <RouterProvider preload={preload}>
          <App />
        </RouterProvider>
      </QueryClientProvider>
    </StrictMode>,
  );
}
