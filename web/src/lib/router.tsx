import {
  type AnchorHTMLAttributes,
  type MouseEvent,
  type ReactNode,
  createContext,
  use,
  useEffect,
  useMemo,
  useState,
  useTransition,
} from "react";

const NAVIGATED = "satyaapply:navigated";

export type PageProps = { params: readonly string[] };

type Preload = (to: string) => Promise<unknown>;
type Location = { url: URL; pending: boolean; preload: Preload };

const LocationContext = createContext<Location | null>(null);

export function navigate(to: string, replace = false): void {
  if (replace) {
    window.history.replaceState(null, "", to);
  } else {
    window.history.pushState(null, "", to);
  }
  window.dispatchEvent(new Event(NAVIGATED));
}

type RouterProps = { preload: Preload; children: ReactNode };

export function RouterProvider({ preload, children }: RouterProps) {
  const [href, setHref] = useState(() => window.location.href);
  const [pending, startTransition] = useTransition();
  useEffect(() => {
    const update = () => {
      void preload(window.location.href);
      startTransition(() => {
        setHref(window.location.href);
      });
    };
    window.addEventListener("popstate", update);
    window.addEventListener(NAVIGATED, update);
    return () => {
      window.removeEventListener("popstate", update);
      window.removeEventListener(NAVIGATED, update);
    };
  }, [preload]);
  const value = useMemo(() => ({ url: new URL(href), pending, preload }), [href, pending, preload]);
  return <LocationContext value={value}>{children}</LocationContext>;
}

export function useLocation(): Location {
  const location = use(LocationContext);
  if (!location) {
    throw new Error("useLocation must be used inside RouterProvider");
  }
  return location;
}

function opensElsewhere(event: MouseEvent<HTMLAnchorElement>): boolean {
  return event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey;
}

type LinkProps = Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href"> & { to: string };

export function Link({ to, onClick, onMouseEnter, onFocus, ...props }: LinkProps) {
  const { preload } = useLocation();
  return (
    <a
      href={to}
      onClick={(event) => {
        onClick?.(event);
        if (event.defaultPrevented || opensElsewhere(event)) {
          return;
        }
        event.preventDefault();
        navigate(to);
      }}
      onMouseEnter={(event) => {
        onMouseEnter?.(event);
        void preload(to);
      }}
      onFocus={(event) => {
        onFocus?.(event);
        void preload(to);
      }}
      {...props}
    />
  );
}
