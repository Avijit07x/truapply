import { create } from "zustand";
import { persist } from "zustand/middleware";

type SeenState = { seen: Record<string, string>; mark: (tab: string) => void };

export const useSeen = create<SeenState>()(
  persist(
    (set) => ({
      seen: {},
      mark: (tab) => {
        set((state) => ({ seen: { ...state.seen, [tab]: new Date().toISOString() } }));
      },
    }),
    { name: "satyaapply-seen" },
  ),
);
