import { useSuspenseQuery } from "@tanstack/react-query";
import { queries } from "../../api/queries";
import { when } from "../../lib/format";
import type { PageProps } from "../../lib/router";
import { BackLink, PageHeader } from "../../ui/Blocks";
import { LogView } from "./LogView";
import styles from "./Runs.module.css";

export default function RunLogPage({ params }: PageProps) {
  const { data: log } = useSuspenseQuery(queries.runLog(params[0] ?? ""));
  return (
    <div className={styles.page}>
      <PageHeader
        back={<BackLink to="/runs">Run</BackLink>}
        title="Run log"
        description={`Finished ${when(log.finishedAt)}.`}
      />
      <LogView lines={log.lines} />
    </div>
  );
}
