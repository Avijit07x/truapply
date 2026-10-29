import type { ReactNode } from "react";
import { cx } from "../lib/cx";
import { pageName } from "../lib/pages";
import { Link, cameFrom } from "../lib/router";
import styles from "./Blocks.module.css";
import { ArrowLeft } from "./icons";

type PageHeaderProps = {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  back?: ReactNode;
};

export function PageHeader({ title, description, actions, back }: PageHeaderProps) {
  return (
    <header className={styles.header}>
      {back}
      <div className={styles.titleRow}>
        <h1 className={styles.title}>{title}</h1>
        {description && <span className={styles.inlineNote}>{description}</span>}
        {actions && <Row>{actions}</Row>}
      </div>
    </header>
  );
}

type SectionProps = { title: ReactNode; aside?: ReactNode; children: ReactNode };

export function Section({ title, aside, children }: SectionProps) {
  return (
    <section className={styles.section}>
      <header className={styles.sectionHead}>
        <h2 className={styles.sectionTitle}>{title}</h2>
        {aside}
      </header>
      {children}
    </section>
  );
}

export function Card({ title, children }: { title?: ReactNode; children: ReactNode }) {
  return (
    <div className={styles.card}>
      {title && <h2 className={styles.cardTitle}>{title}</h2>}
      {children}
    </div>
  );
}

export function Note({ children }: { children: ReactNode }) {
  return <p className={styles.note}>{children}</p>;
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className={styles.empty}>{children}</p>;
}

export function Row({ children, align }: { children: ReactNode; align?: "end" }) {
  return <div className={cx(styles.row, align === "end" && styles.end)}>{children}</div>;
}

export function Stack({ children }: { children: ReactNode }) {
  return <div className={styles.stack}>{children}</div>;
}

export function List({ children, label }: { children: ReactNode; label?: string }) {
  return (
    <ul className={styles.list} aria-label={label}>
      {children}
    </ul>
  );
}

export function BackLink({ to, children }: { to: string; children: ReactNode }) {
  return (
    <Link to={to} className={styles.back}>
      <ArrowLeft size={12} />
      {children}
    </Link>
  );
}

export function BackToWhereYouWere({ fallback }: { fallback: string }) {
  const from = cameFrom();
  const page = from ? new URL(from, window.location.origin).pathname : fallback;
  const name = pageName(page);
  if (!from || !name) return <BackLink to={fallback}>{pageName(fallback) ?? "Back"}</BackLink>;
  return (
    <a
      href={from}
      className={styles.back}
      onClick={(event) => {
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey) return;
        event.preventDefault();
        window.history.back();
      }}
    >
      <ArrowLeft size={12} />
      {name}
    </a>
  );
}
