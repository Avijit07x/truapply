import { useEffect } from "react";

const IDLE = "/favicon.svg";
const RUNNING = "/favicon-running.svg";

export function useRunIcon(running: boolean) {
  useEffect(() => {
    const icon = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
    if (icon) icon.href = running ? RUNNING : IDLE;
  }, [running]);
}
