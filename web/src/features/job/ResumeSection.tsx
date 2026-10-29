import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useJobChange } from "../../api/mutations";
import { queries } from "../../api/queries";
import type { JobDetail } from "../../api/types";
import { RuleForm } from "../../components/RuleForm";
import { cx } from "../../lib/cx";
import { Empty, Note, Row, Stack } from "../../ui/Blocks";
import { Button } from "../../ui/Button";
import { Callout } from "../../ui/Callout";
import { Dialog } from "../../ui/Dialog";
import { ExternalLink } from "../../ui/ExternalLink";
import { Check, ChevronDown, Spark, Undo } from "../../ui/icons";
import { toast } from "../../ui/toasts";
import styles from "./Job.module.css";

const FOLD_AFTER = 4;

const LINE_LOOK: Partial<Record<string, string>> = { "+": styles.added, "-": styles.removed };
import { Panel } from "./Panel";

function TailorNow({ job }: { job: JobDetail }) {
  const change = useJobChange(job.id);
  const settings = useQuery(queries.settings());
  const tailors = settings.data?.values.tailorResume ?? true;
  const [asked, setAsked] = useState(false);
  if (asked && !change.isPending && !change.isError) {
    return (
      <Empty>
        {tailors
          ? "Tailoring your resume now. It shows here in about a minute."
          : "Getting it ready with your original resume. It shows here in a moment."}
      </Empty>
    );
  }
  return (
    <div className={styles.tailorNow}>
      <span>{tailors ? "Not tailored yet." : "You send your resume as it is."}</span>
      <Button
        variant="primary"
        icon={tailors ? <Spark /> : <Check />}
        busy={change.isPending}
        onClick={() => {
          setAsked(true);
          change.mutate({ action: "tailor" });
        }}
      >
        {tailors ? "Tailor my resume" : "Get it ready"}
      </Button>
    </div>
  );
}

function Changes({ job }: { job: JobDetail }) {
  if (job.changes === null) {
    if (job.hasResume) return <Note>Your original resume is used for this job.</Note>;
    if (job.actions.includes("tailor")) return <TailorNow job={job} />;
    return <Empty>Not tailored yet. Good matches are tailored on the next run.</Empty>;
  }
  if (job.changes.length === 0) {
    return <Note>Tailored, but nothing changed from your original.</Note>;
  }
  return <Folded lines={job.changes} />;
}

function Folded({ lines }: { lines: readonly string[] }) {
  const [open, setOpen] = useState(false);
  const folds = lines.length > FOLD_AFTER;
  return (
    <div className={styles.foldWrap}>
      <ul
        id="resume-changes"
        className={cx(styles.diff, folds && !open && styles.folded)}
        aria-label="What changed in your resume"
      >
        {lines.map((line, index) => (
          <li key={`${String(index)}-${line}`} className={LINE_LOOK[line.charAt(0)] ?? styles.same}>
            {LINE_LOOK[line.charAt(0)] ? line.slice(1) : line}
          </li>
        ))}
      </ul>
      {folds && (
        <button
          type="button"
          className={styles.unfold}
          aria-expanded={open}
          aria-controls="resume-changes"
          onClick={() => {
            setOpen(!open);
          }}
        >
          {open ? "Show less" : `Show all ${String(lines.length)} changes`}
          <ChevronDown size={12} className={cx(styles.unfoldIcon, open && styles.flipped)} />
        </button>
      )}
    </div>
  );
}

export function resumeApplies(job: JobDetail): boolean {
  return (
    job.changes !== null || job.hasResume || job.actions.includes("tailor") || job.status === "new"
  );
}

export function ResumeSection({ job }: { job: JobDetail }) {
  const change = useJobChange(job.id);
  const [confirming, setConfirming] = useState(false);
  const [reverted, setReverted] = useState(false);
  const close = () => {
    setConfirming(false);
  };
  return (
    <Panel
      title="Resume"
      aside={
        job.hasResume && (
          <ExternalLink href={`/jobs/${String(job.id)}/resume.pdf`}>Open the PDF</ExternalLink>
        )
      }
    >
      <Stack>
        <Changes job={job} />
        {job.actions.includes("revert") && (
          <Row>
            <Button
              icon={<Undo size={14} />}
              onClick={() => {
                setConfirming(true);
              }}
            >
              Use my original resume
            </Button>
          </Row>
        )}
        {reverted && (
          <Callout>Tell it what went wrong, so the next tailored resume is better.</Callout>
        )}
        <div className={styles.note}>
          <RuleForm kind="tailoring_note" compact autoFocus={reverted} key={String(reverted)} />
        </div>
      </Stack>
      <Dialog open={confirming} title="Use your original resume?" onClose={close}>
        <Note>This job gets your original resume. The tailored version is deleted.</Note>
        <Row>
          <Button
            variant="primary"
            busy={change.isPending}
            onClick={() => {
              change.mutate(
                { action: "revert" },
                {
                  onSuccess: () => {
                    close();
                    setReverted(true);
                    toast("This job now uses your original resume.");
                  },
                },
              );
            }}
          >
            Use original
          </Button>
          <Button variant="ghost" onClick={close}>
            Cancel
          </Button>
        </Row>
      </Dialog>
    </Panel>
  );
}
