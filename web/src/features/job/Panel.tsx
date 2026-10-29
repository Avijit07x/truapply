import type { ReactNode } from "react";
import styles from "./Job.module.css";

type PanelProps = { title: ReactNode; aside?: ReactNode; children: ReactNode };

export function Panel({ title, aside, children }: PanelProps) {
  return (
    <section className={styles.panel}>
      <header className={styles.panelHead}>
        <h2 className={styles.panelTitle}>{title}</h2>
        {aside}
      </header>
      <div className={styles.panelBody}>{children}</div>
    </section>
  );
}
