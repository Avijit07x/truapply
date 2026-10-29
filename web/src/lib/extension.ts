import { useEffect, useState } from "react";

const HELLO = "truapply:hello";
const HERE = "truapply:here";
const ASK_EVERY_MS = 1_500;

export function useExtensionHere(): boolean {
  const [here, setHere] = useState(false);
  useEffect(() => {
    if (here) return;
    const heard = (event: MessageEvent) => {
      if (event.source === window && event.data === HERE) setHere(true);
    };
    const ask = () => {
      window.postMessage(HELLO, window.location.origin);
    };
    window.addEventListener("message", heard);
    ask();
    const timer = setInterval(ask, ASK_EVERY_MS);
    return () => {
      clearInterval(timer);
      window.removeEventListener("message", heard);
    };
  }, [here]);
  return here;
}
