import { CSPProvider } from "@base-ui/react/csp-provider";
import { useQuery } from "@tanstack/react-query";
import { type ComponentType, type ReactNode, useEffect } from "react";
import { queries } from "../api/queries";
import { sourceLabel } from "../domain/sources";
import { cx } from "../lib/cx";
import { useSeen } from "../lib/seen";
import { Link, useLocation } from "../lib/router";
import { Toaster } from "../ui/Toaster";
import { ThemeSwitch } from "./ThemeSwitch";
import { PAGE_NAMES, sitePage } from "../lib/pages";
import {
  Columns,
  Flow,
  Home,
  type IconProps,
  Inbox,
  Play,
  Rows,
  Sliders,
  Spark,
} from "../ui/icons";
import styles from "./Layout.module.css";
import { useLiveRefresh } from "./useLiveRefresh";

type NavItem = { to: string; label: string; Icon: ComponentType<IconProps>; tab?: string };

const NAV: readonly NavItem[] = [
  { to: "/", label: PAGE_NAMES["/"], Icon: Home },
  { to: "/board", label: PAGE_NAMES["/board"], Icon: Columns },
  { to: "/workflow", label: PAGE_NAMES["/workflow"], Icon: Flow },
  { to: "/jobs", label: PAGE_NAMES["/jobs"], Icon: Rows, tab: "jobs" },
  { to: "/runs", label: PAGE_NAMES["/runs"], Icon: Play },
  { to: "/learned", label: PAGE_NAMES["/learned"], Icon: Spark },
  { to: "/settings", label: PAGE_NAMES["/settings"], Icon: Sliders },
];

const CAREER_JOBS = NAV.findIndex((item) => item.to === "/jobs") + 1;

function withSites(sources: readonly string[]): NavItem[] {
  const sites = sources.map((source) => ({
    to: sitePage(source),
    label: sourceLabel(source),
    Icon: Inbox,
    tab: source,
  }));
  return [...NAV.slice(0, CAREER_JOBS), ...sites, ...NAV.slice(CAREER_JOBS)];
}

function section(nav: readonly NavItem[], path: string): string {
  const match = nav.find((item) => item.to !== "/" && path.startsWith(item.to));
  return match?.to ?? "/";
}

function useFresh(nav: readonly NavItem[], active: string): Record<string, number> {
  const { seen, mark } = useSeen();
  const tabs = nav.flatMap((item) => (item.tab ? [item.tab] : []));
  const current = nav.find((item) => item.to === active)?.tab;
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
  const { data } = useQuery({ ...queries.newJobs(known), enabled: tabs.length > 0 });
  return data ?? {};
}

export type PageLayout = "page" | "fit" | "bleed";

type LayoutProps = { path: string; layout: PageLayout; children: ReactNode };

export function Layout({ path, layout, children }: LayoutProps) {
  const { pending } = useLocation();
  const running = useLiveRefresh();
  const { data: summary } = useQuery(queries.summary());
  const nav = withSites(summary?.sites.map((site) => site.source) ?? []);
  const active = section(nav, path);
  const fresh = useFresh(nav, active);
  return (
    <CSPProvider disableStyleElements>
      <div className={styles.app}>
        <a className={styles.skip} href="#content">
          Skip to content
        </a>
        <aside className={styles.sidebar}>
          <Link to="/" className={styles.brand}>
            <span className={styles.mark} aria-hidden="true">
              S
            </span>
            <span className={styles.brandName}>SatyaApply</span>
          </Link>
          <nav className={styles.nav} aria-label="Main">
            {nav.map(({ to, label, Icon, tab }) => (
              <Link
                key={to}
                to={to}
                className={styles.navLink}
                aria-current={to === active ? "page" : undefined}
              >
                <Icon />
                <span className={styles.navLabel}>{label}</span>
                {tab && (fresh[tab] ?? 0) > 0 && to !== active && (
                  <span className={styles.badge} aria-label={`${String(fresh[tab])} new`}>
                    {fresh[tab]}
                  </span>
                )}
              </Link>
            ))}
          </nav>
          {running && (
            <Link to="/runs" className={styles.running}>
              <span className={styles.pip} aria-hidden="true" />
              <span className={styles.navLabel}>Run in progress</span>
            </Link>
          )}
          <div className={styles.bottom}>
            <ThemeSwitch />
            <p className={styles.foot}>
              Runs on your computer. You press Submit on every application.
            </p>
          </div>
        </aside>
        <main
          id="content"
          className={cx(
            styles.content,
            layout === "bleed" && styles.bleed,
            layout === "fit" && styles.fit,
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
