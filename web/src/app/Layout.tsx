import { CSPProvider } from "@base-ui/react/csp-provider";
import type { ComponentType, ReactNode } from "react";
import { cx } from "../lib/cx";
import { Link, useLocation } from "../lib/router";
import { Toaster } from "../ui/Toaster";
import { ThemeSwitch } from "./ThemeSwitch";
import { Columns, Flow, Home, type IconProps, Play, Rows, Sliders, Spark } from "../ui/icons";
import styles from "./Layout.module.css";
import { useLiveRefresh } from "./useLiveRefresh";

type NavItem = { to: string; label: string; Icon: ComponentType<IconProps> };

const NAV: readonly NavItem[] = [
  { to: "/", label: "Home", Icon: Home },
  { to: "/board", label: "Board", Icon: Columns },
  { to: "/workflow", label: "Workflow", Icon: Flow },
  { to: "/jobs", label: "All jobs", Icon: Rows },
  { to: "/runs", label: "Run", Icon: Play },
  { to: "/learned", label: "Learned", Icon: Spark },
  { to: "/settings", label: "Settings", Icon: Sliders },
];

function section(path: string): string {
  const match = NAV.find((item) => item.to !== "/" && path.startsWith(item.to));
  return match?.to ?? "/";
}

type LayoutProps = { path: string; bleed: boolean; children: ReactNode };

export function Layout({ path, bleed, children }: LayoutProps) {
  const { pending } = useLocation();
  const running = useLiveRefresh();
  const active = section(path);
  return (
    <CSPProvider disableStyleElements>
      <div className={cx(styles.app, bleed && styles.rail)}>
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
                title={bleed ? label : undefined}
                aria-current={to === active ? "page" : undefined}
              >
                <Icon />
                <span className={styles.navLabel}>{label}</span>
              </Link>
            ))}
          </nav>
          {running && (
            <Link
              to="/runs"
              className={styles.running}
              title={bleed ? "Run in progress" : undefined}
            >
              <span className={styles.pip} aria-hidden="true" />
              <span className={styles.navLabel}>Run in progress</span>
            </Link>
          )}
          <div className={styles.bottom}>
            <ThemeSwitch compact={bleed} />
            <p className={styles.foot}>Runs on your computer. Nothing is sent without your OK.</p>
          </div>
        </aside>
        <main
          id="content"
          className={cx(styles.content, bleed && styles.bleed)}
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
