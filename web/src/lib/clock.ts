import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Clock = "system" | "12" | "24";

type ClockState = { clock: Clock; setClock: (clock: Clock) => void };

export const useClock = create<ClockState>()(
  persist(
    (set) => ({
      clock: "system",
      setClock: (clock) => {
        set({ clock });
      },
    }),
    { name: "satyaapply-clock" },
  ),
);
