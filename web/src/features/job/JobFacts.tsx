import type { ReactNode } from "react";
import type { JobDetail } from "../../api/types";
import { StatusPill } from "../../components/StatusPill";
import { sourceLabel } from "../../domain/sources";
import { when } from "../../lib/format";
import { Note, Row } from "../../ui/Blocks";
import { Callout } from "../../ui/Callout";
import { ExternalLink } from "../../ui/ExternalLink";
import { Spark } from "../../ui/icons";
import styles from "./Job.module.css";

function links(job: JobDetail): ReactNode {
  if (!job.url && !job.applyUrl) {
    return "None";
  }
  return (
    <Row>
      {job.url && <ExternalLink href={job.url}>Job post</ExternalLink>}
      {job.applyUrl && <ExternalLink href={job.applyUrl}>Application form</ExternalLink>}
    </Row>
  );
}

export function JobFacts({ job }: { job: JobDetail }) {
  const facts: readonly (readonly [string, ReactNode])[] = [
    ["Status", <StatusPill key="status" status={job.status} />],
    ["Score", job.score ?? "Not scored yet"],
    ["Found on", sourceLabel(job.source)],
    ["Updated", when(job.updatedAt)],
    ["Links", links(job)],
  ];
  const lastStep = job.note && job.note !== job.reason ? job.note : "";
  return (
    <div className={styles.factsBlock}>
      <dl className={styles.facts}>
        {facts.map(([label, value]) => (
          <div key={label} className={styles.fact}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      {job.reason && (
        <Callout icon={<Spark />}>
          <p>
            <strong>Why this score: </strong>
            {job.reason}
          </p>
        </Callout>
      )}
      {lastStep && <Note>Last step: {lastStep}</Note>}
    </div>
  );
}
