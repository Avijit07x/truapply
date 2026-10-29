import { CSPProvider } from "@base-ui/react/csp-provider";
import { useQuery } from "@tanstack/react-query";
import { type ComponentType, type ReactNode, useEffect, useMemo } from "react";
import { queries } from "../api/queries";
import { cx } from "../lib/cx";
import { useSeen } from "../lib/seen";
import { Link, useLocation } from "../lib/router";
import { Logo } from "../ui/Logo";
import { Toaster } from "../ui/Toaster";
import { SidebarRun } from "./SidebarRun";
import { ThemeSwitch } from "./ThemeSwitch";
import { PAGE_NAMES } from "../lib/pages";
import {
  Briefcase,
  Building,
  Home,
  type IconProps,
  Pulse,
  Rows,
  Sliders,
  Spark,
} from "../ui/icons";
import styles from "./Layout.module.css";
import { useLiveRefresh } from "./useLiveRefresh";
import { useRunIcon } from "./useRunIcon";

const TABLE = "/jobs/table";

type NavItem = { to: string; label: string; Icon: ComponentType<IconProps>; also?: string };

const MAIN: readonly NavItem[] = [
  { to: "/", label: PAGE_NAMES["/"], Icon: Home },
  { to: "/jobs", label: "Jobs", Icon: Briefcase, also: "/sites/" },
  { to: TABLE, label: PAGE_NAMES[TABLE], Icon: Rows },
  { to: "/companies", label: PAGE_NAMES["/companies"], Icon: Building },
  { to: "/runs", label: PAGE_NAMES["/runs"], Icon: Pulse },
];

const YOU: readonly NavItem[] = [
  { to: "/learned", label: PAGE_NAMES["/learned"], Icon: Spark },
  { to: "/settings", label: PAGE_NAMES["/settings"], Icon: Sliders },
];

const JOBS_TAB = "jobs";

function section(path: string): string {
  if (path.endsWith("/table")) return TABLE;
  const match = [...MAIN, ...YOU].find((item) =>
    item.to === "/"
      ? path === "/"
      : path.startsWith(item.to) || (item.also !== undefined && path.startsWith(item.also)),
  );
  return match?.to ?? "";
}

function tabOf(path: string): string | undefined {
  if (path.startsWith("/sites/") && !path.endsWith("/table")) return path.slice("/sites/".length);
  return path === "/jobs" ? JOBS_TAB : undefined;
}

function useFresh(sites: readonly string[], path: string): number {
  const { seen, mark } = useSeen();
  const key = sites.join(",");
  const tabs = useMemo(() => [JOBS_TAB, ...key.split(",").filter(Boolean)], [key]);
  const current = tabOf(path);
  useEffect(() => {
    for (const tab of tabs) {
      if (!seen[tab]) {
        mark(tab);
      }
    }
  }, [tabs, seen, mark]);
  useEffect(() => {
    if (!current) {
      return undefined;
    }
    mark(current);
    return () => {
      mark(current);
    };
  }, [current, mark]);
  const known = Object.fromEntries(tabs.flatMap((tab) => (seen[tab] ? [[tab, seen[tab]]] : [])));
  const { data } = useQuery(queries.newJobs(known));
  return Object.entries(data ?? {}).reduce(
    (sum, [tab, count]) => (tab === current ? sum : sum + count),
    0,
  );
}

function NavLinks({
  items,
  active,
  fresh,
}: {
  items: readonly NavItem[];
  active: string;
  fresh: number;
}) {
  return items.map(({ to, label, Icon }) => (
    <Link
      key={to}
      to={to}
      className={styles.navLink}
      aria-current={to === active ? "page" : undefined}
    >
      <Icon />
      <span className={styles.navLabel}>{label}</span>
      {to === "/jobs" && fresh > 0 && (
        <span className={styles.badge} aria-label={`${String(fresh)} new`}>
          {fresh}
        </span>
      )}
    </Link>
  ));
}

export type PageLayout = "page" | "fit" | "bleed" | "flush";

type LayoutProps = { path: string; layout: PageLayout; children: ReactNode };

export function Layout({ path, layout, children }: LayoutProps) {
  const { pending } = useLocation();
  const running = useLiveRefresh();
  useRunIcon(running);
  const { data: summary } = useQuery(queries.summary());
  const active = section(path);
  const fresh = useFresh(summary?.sites.map((site) => site.source) ?? [], path);
  return (
    <CSPProvider disableStyleElements>
      <div className={styles.app}>
        <a className={styles.skip} href="#content">
          Skip to content
        </a>
        <aside className={styles.sidebar}>
          <Link to="/" className={styles.brand}>
            <Logo />
            <span className={styles.brandName}>TruApply</span>
          </Link>
          <nav className={styles.nav} aria-label="Main">
            <NavLinks items={MAIN} active={active} fresh={fresh} />
            <span className={styles.navGroup}>You</span>
            <NavLinks items={YOU} active={active} fresh={fresh} />
          </nav>
          <div className={styles.bottom}>
            {summary && <SidebarRun run={summary.run} here={active === "/runs"} />}
            <div className={styles.themeRow}>
              <span>Theme</span>
              <ThemeSwitch />
            </div>
          </div>
        </aside>
        <main
          id="content"
          className={cx(
            styles.content,
            layout === "bleed" && styles.bleed,
            layout === "fit" && styles.fit,
            layout === "flush" && styles.flush,
          )}
          aria-busy={pending}
        >
          {pending && <div className={styles.progress} aria-hidden="true" />}
          {children}
        </main>
        <Toaster />
      </div>
    </CSPProvider>
  );
}
