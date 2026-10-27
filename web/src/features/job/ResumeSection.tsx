import { useState } from "react";
import { useJobChange } from "../../api/mutations";
import type { JobDetail } from "../../api/types";
import { RuleForm } from "../../components/RuleForm";
import { Empty, Note, Row, Section, Stack } from "../../ui/Blocks";
import { Button } from "../../ui/Button";
import { Callout } from "../../ui/Callout";
import { Dialog } from "../../ui/Dialog";
import { ExternalLink } from "../../ui/ExternalLink";
import { Spark, Undo } from "../../ui/icons";
import { toast } from "../../ui/toasts";
import styles from "./Job.module.css";

function TailorNow({ job }: { job: JobDetail }) {
  const change = useJobChange(job.id);
  const [asked, setAsked] = useState(false);
  if (asked && !change.isPending && !change.isError) {
    return <Empty>Tailoring your resume now. It shows here in about a minute.</Empty>;
  }
  return (
    <div className={styles.tailorNow}>
      <span>Not tailored yet.</span>
      <Button
        variant="primary"
        icon={<Spark />}
        busy={change.isPending}
        onClick={() => {
          setAsked(true);
          change.mutate({ action: "tailor" });
        }}
      >
        Tailor my resume
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
  return (
    <pre className={styles.diff} aria-label="What changed in your resume">
      {job.changes.map((line, index) => (
        <span
          key={`${String(index)}-${line}`}
          className={line.startsWith("+") ? styles.added : styles.removed}
        >
          {line}
          {"\n"}
        </span>
      ))}
    </pre>
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
    <Section
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
    </Section>
  );
}
