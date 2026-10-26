import { useQuery } from "@tanstack/react-query";
import { queries } from "../../api/queries";
import type { Group } from "../../api/types";
import { JobList } from "../../components/JobList";
import { GROUP_LABEL } from "../../domain/groups";
import { Note } from "../../ui/Blocks";
import { ButtonLink, IconButton } from "../../ui/Button";
import { Close } from "../../ui/icons";
import { EXPLAIN } from "./flow";
import styles from "./Workflow.module.css";

const PREVIEW = 5;

type InspectorProps = { group: Group; count: number; onClose: () => void };

export function Inspector({ group, count, onClose }: InspectorProps) {
  const { data, isPending } = useQuery(queries.jobs({ group }));
  return (
    <aside className={styles.inspector} aria-label={GROUP_LABEL[group]}>
      <header className={styles.inspectorHead}>
        <span className={styles.tag}>Your jobs</span>
        <IconButton label="Close" onClick={onClose}>
          <Close size={12} />
        </IconButton>
      </header>
      <h2 className={styles.inspectorTitle}>{GROUP_LABEL[group]}</h2>
      <p className={styles.inspectorCount}>{count.toLocaleString()}</p>
      <Note>{EXPLAIN[group]}</Note>
      {isPending ? (
        <span className={styles.loading}>Loading jobs</span>
      ) : (
        <JobList
          jobs={data?.jobs.slice(0, PREVIEW) ?? []}
          empty="No jobs here yet."
          showStatus={false}
        />
      )}
      {count > 0 && (
        <ButtonLink to={`/jobs?group=${group}`} variant="primary">
          See all {count.toLocaleString()}
        </ButtonLink>
      )}
    </aside>
  );
}
