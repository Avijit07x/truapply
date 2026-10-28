import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Theme = "light" | "dark" | "system";

export const THEMES: readonly Theme[] = ["light", "dark", "system"];

type ThemeState = { theme: Theme; setTheme: (theme: Theme) => void };

export const useTheme = create<ThemeState>()(
  persist(
    (set) => ({
      theme: "light",
      setTheme: (theme) => {
        set({ theme });
      },
    }),
    { name: "truapply-theme" },
  ),
);

function apply(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
}

export function syncTheme(): void {
  apply(useTheme.getState().theme);
  useTheme.subscribe((state) => {
    apply(state.theme);
  });
}
