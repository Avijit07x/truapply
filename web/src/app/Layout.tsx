import { CSPProvider } from "@base-ui/react/csp-provider";
import type { ComponentType, ReactNode } from "react";
import { cx } from "../lib/cx";
import { Link, useLocation } from "../lib/router";
import { Toaster } from "../ui/Toaster";
import { ThemeSwitch } from "./ThemeSwitch";
import { PAGE_NAMES } from "../lib/pages";
import { Columns, Flow, Home, type IconProps, Play, Rows, Sliders, Spark } from "../ui/icons";
import styles from "./Layout.module.css";
import { useLiveRefresh } from "./useLiveRefresh";

type NavItem = { to: string; label: string; Icon: ComponentType<IconProps> };

const NAV: readonly NavItem[] = [
  { to: "/", label: PAGE_NAMES["/"], Icon: Home },
  { to: "/board", label: PAGE_NAMES["/board"], Icon: Columns },
  { to: "/workflow", label: PAGE_NAMES["/workflow"], Icon: Flow },
  { to: "/jobs", label: PAGE_NAMES["/jobs"], Icon: Rows },
  { to: "/runs", label: PAGE_NAMES["/runs"], Icon: Play },
  { to: "/learned", label: PAGE_NAMES["/learned"], Icon: Spark },
  { to: "/settings", label: PAGE_NAMES["/settings"], Icon: Sliders },
];

function section(path: string): string {
  const match = NAV.find((item) => item.to !== "/" && path.startsWith(item.to));
  return match?.to ?? "/";
}

export type PageLayout = "page" | "fit" | "bleed";

type LayoutProps = { path: string; layout: PageLayout; children: ReactNode };

export function Layout({ path, layout, children }: LayoutProps) {
  const { pending } = useLocation();
  const running = useLiveRefresh();
  const active = section(path);
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
            {NAV.map(({ to, label, Icon }) => (
              <Link
                key={to}
                to={to}
                className={styles.navLink}
                aria-current={to === active ? "page" : undefined}
              >
                <Icon />
                <span className={styles.navLabel}>{label}</span>
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
