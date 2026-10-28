import { useQuery } from "@tanstack/react-query";
import { useRunStart } from "../../api/mutations";
import { queries } from "../../api/queries";
import type { Group, RunStage, RunState, SettingsView, Workflow } from "../../api/types";
import { JobList } from "../../components/JobList";
import { GROUP_LABEL } from "../../domain/groups";
import { Link } from "../../lib/router";
import { Ago } from "../../ui/Ago";
import { Note } from "../../ui/Blocks";
import { Button, ButtonLink, IconButton } from "../../ui/Button";
import { Callout } from "../../ui/Callout";
import { Close, Play } from "../../ui/icons";
import { toast } from "../../ui/toasts";
import {
  AutoSubmit,
  FormAnswers,
  type GroupProps,
  WorkPlaces,
  fieldsFor,
} from "../settings/SettingsGroups";
import { useSettingsDraft } from "../settings/useSettingsDraft";
import {
  EXPLAIN,
  OUTCOMES,
  PANELS,
  RUN_LABEL,
  STEPS,
  STEP_EXPLAIN,
  type SettingsPart,
} from "./flow";
import { GROUP_OF } from "./graph";
import styles from "./Workflow.module.css";

const PREVIEW = 5;
const SKIP_REASONS = [
  "wrong_title",
  "wrong_place",
  "too_old",
  "skipped_company",
] as const satisfies readonly Group[];

type Counts = Workflow["groups"];
type InspectorProps = {
  node: string;
  counts: Counts;
  lastRun: Workflow["lastRun"];
  run: RunState | undefined;
  onClose: () => void;
};

function SkipReasons({ counts }: { counts: Counts }) {
  const reasons = [...SKIP_REASONS].sort((a, b) => counts[b] - counts[a]);
  const sorted = reasons.reduce((sum, reason) => sum + counts[reason], 0);
  const unsorted = counts.skipped - sorted;
  return (
    <ul className={styles.reasons} aria-label="Why they were skipped">
      {reasons.map((reason) => (
        <li key={reason}>
          <Link to={`/jobs?group=${reason}`} className={styles.reason}>
            <span>{GROUP_LABEL[reason]}</span>
            <span className={styles.reasonCount}>{counts[reason].toLocaleString()}</span>
          </Link>
        </li>
      ))}
      {unsorted > 0 && (
        <li className={styles.reason}>
          <span>Not sorted yet, sorted on the next run</span>
          <span className={styles.reasonCount}>{unsorted.toLocaleString()}</span>
        </li>
      )}
    </ul>
  );
}

function Jobs({ group, counts }: { group: Group; counts: Counts }) {
  const { data, isPending } = useQuery(queries.jobs({ group }));
  const count = counts[group];
  return (
    <>
      {group === "skipped" ? (
        <SkipReasons counts={counts} />
      ) : isPending ? (
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
    </>
  );
}

function LastRun({
  added,
  startedAt,
  running,
}: {
  added: number;
  startedAt: string;
  running: boolean;
}) {
  return (
    <p className={styles.loading}>
      {running ? "This run so far" : "Latest run"}, started <Ago iso={startedAt} />:{" "}
      {added > 0 ? `+${added.toLocaleString()}` : "none added"}
    </p>
  );
}

function RunStep({ stage, run }: { stage: RunStage; run: RunState | undefined }) {
  const start = useRunStart();
  const running = run?.running ?? false;
  return (
    <Button
      icon={<Play size={14} />}
      busy={start.isPending}
      disabled={!run || running}
      title={running ? "Wait for the run that's going to finish." : undefined}
      onClick={() => {
        if (!run) {
          return;
        }
        start.mutate(
          { limit: run.limits.default, search: false, only: stage },
          {
            onSuccess: () => {
              toast("Started. The box lights up while it works.");
            },
          },
        );
      }}
    >
      {RUN_LABEL[stage]}
    </Button>
  );
}

function Fields({ part, group }: { part: SettingsPart; group: GroupProps }) {
  const { tags, number } = fieldsFor(group);
  switch (part) {
    case "search":
      return (
        <>
          {tags("titleKeywords", "Title keywords")}
          {tags("titleExclude", "Titles to skip")}
          {tags("skipCompanies", "Companies to skip")}
          {number("maxJobAgeDays", "Oldest job to consider, in days")}
          <WorkPlaces {...group} />
        </>
      );
    case "scoring":
      return (
        <>
          {number("minScore", "Minimum match score")}
          {number("scoresPerRun", "Jobs to score each run")}
        </>
      );
    case "tailoring":
      return number("jobsPerRun", "Jobs to get ready each run");
    case "applying":
      return (
        <>
          <AutoSubmit {...group} />
          <FormAnswers {...group} />
        </>
      );
  }
}

function StepForm({ view, part }: { view: SettingsView; part: SettingsPart }) {
  const form = useSettingsDraft(view, () => {
    toast("Saved. It's used from the next run.");
  });
  return (
    <form
      className={styles.panelForm}
      aria-label="Settings for this step"
      onSubmit={(event) => {
        event.preventDefault();
        form.submit();
      }}
    >
      <span className={styles.tag}>Settings for this step</span>
      <Fields part={part} group={form.group} />
      {form.problems.length > 0 && (
        <Callout tone="bad">
          <ul>
            {form.problems.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </Callout>
      )}
      <div className={styles.panelSave}>
        <span role="status">
          {form.dirty ? "You have unsaved changes." : "Everything is saved."}
        </span>
        <Button type="submit" variant="primary" busy={form.saving} disabled={!form.dirty}>
          Save
        </Button>
      </div>
    </form>
  );
}

function StepSettings({ part }: { part: SettingsPart }) {
  const { data } = useQuery(queries.settings());
  return data ? <StepForm view={data} part={part} /> : null;
}

function titleOf(node: string, group: Group | undefined): string {
  if (group) {
    return GROUP_LABEL[group];
  }
  return (
    STEPS.find((step) => step.id === node)?.title ??
    OUTCOMES.find((item) => item.id === node)?.title ??
    ""
  );
}

export function Inspector({ node, counts, lastRun, run, onClose }: InspectorProps) {
  const group = GROUP_OF.get(node);
  const panel = PANELS[node];
  const explain = group ? EXPLAIN[group] : STEP_EXPLAIN[node];
  return (
    <aside className={styles.inspector} aria-label={titleOf(node, group)}>
      <header className={styles.inspectorHead}>
        <span className={styles.tag}>{group ? "Your jobs" : "Step"}</span>
        <IconButton label="Close" onClick={onClose}>
          <Close size={12} />
        </IconButton>
      </header>
      <h2 className={styles.inspectorTitle}>{titleOf(node, group)}</h2>
      {group && <p className={styles.inspectorCount}>{counts[group].toLocaleString()}</p>}
      {explain && <Note>{explain}</Note>}
      {group && lastRun && (
        <LastRun
          added={lastRun.groups[group]}
          startedAt={lastRun.startedAt}
          running={run?.running ?? false}
        />
      )}
      {panel?.stage && <RunStep stage={panel.stage} run={run} />}
      {group && <Jobs group={group} counts={counts} />}
      {panel && <StepSettings part={panel.settings} />}
    </aside>
  );
}
