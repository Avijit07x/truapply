import { Tabs } from "@base-ui/react/tabs";
import { useId } from "react";
import type { Column, Status } from "../../api/types";
import { JobList } from "../../components/JobList";
import { Link } from "../../lib/router";
import { Note } from "../../ui/Blocks";
import { ArrowRight, Inbox } from "../../ui/icons";
import styles from "./Home.module.css";

type Tab = { status: Status; label: string; empty: string; hint?: string };

const TABS: readonly Tab[] = [
  { status: "needs_input", label: "Answer", empty: "No questions waiting for you." },
  {
    status: "finish",
    label: "Finish",
    empty: "Nothing to finish by hand.",
    hint: "Filled in, but the site wants you to prove you're human. Open it in your own browser and submit.",
  },
  {
    status: "ready",
    label: "Approve",
    empty: "Nothing waiting for your OK. New ones show up after a run.",
  },
];

const NOTHING: Column = { status: "ready", total: 0, jobs: [] };

function Panel({ tab, column }: { tab: Tab; column: Column }) {
  if (column.total === 0) {
    return (
      <div className={styles.calm}>
        <span className={styles.calmIcon}>
          <Inbox size={18} />
        </span>
        <p>{tab.empty}</p>
      </div>
    );
  }
  return (
    <>
      {tab.hint && <Note>{tab.hint}</Note>}
      <JobList jobs={column.jobs} empty={tab.empty} showStatus={false} />
      {column.total > column.jobs.length && (
        <Link to={`/jobs?status=${tab.status}`} className={styles.more}>
          See all {column.total.toLocaleString()}
          <ArrowRight size={12} />
        </Link>
      )}
    </>
  );
}

export function NeedsYou({ columns }: { columns: readonly Column[] }) {
  const title = useId();
  const tabs = TABS.map((tab) => ({
    tab,
    column: columns.find((column) => column.status === tab.status) ?? NOTHING,
  }));
  const first = tabs.find(({ column }) => column.total > 0)?.tab.status ?? "needs_input";
  return (
    <section className={styles.needs} aria-labelledby={title}>
      <Tabs.Root defaultValue={first}>
        <header className={styles.needsHead}>
          <h2 id={title} className={styles.panelTitle}>
            Needs you
          </h2>
          <Tabs.List className={styles.tabs} aria-label="Jobs waiting on you">
            {tabs.map(({ tab, column }) => (
              <Tabs.Tab key={tab.status} value={tab.status} className={styles.tab}>
                {tab.label}
                <span className={styles.tabCount}>{column.total.toLocaleString()}</span>
              </Tabs.Tab>
            ))}
          </Tabs.List>
        </header>
        {tabs.map(({ tab, column }) => (
          <Tabs.Panel key={tab.status} value={tab.status} className={styles.panel}>
            <Panel tab={tab} column={column} />
          </Tabs.Panel>
        ))}
      </Tabs.Root>
    </section>
  );
}
