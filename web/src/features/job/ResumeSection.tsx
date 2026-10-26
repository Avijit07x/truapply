import { useState } from "react";
import { useJobChange } from "../../api/mutations";
import type { JobDetail } from "../../api/types";
import { RuleForm } from "../../components/RuleForm";
import { Card, Empty, Note, Row, Section, Stack } from "../../ui/Blocks";
import { Button } from "../../ui/Button";
import { Callout } from "../../ui/Callout";
import { Dialog } from "../../ui/Dialog";
import { ExternalLink } from "../../ui/ExternalLink";
import { Undo } from "../../ui/icons";
import { toast } from "../../ui/toasts";
import styles from "./Job.module.css";

function Changes({ job }: { job: JobDetail }) {
  if (job.changes === null) {
    return job.hasResume ? (
      <Note>Your original resume is used for this job.</Note>
    ) : (
      <Empty>Not tailored yet. It's tailored when the form is filled in.</Empty>
    );
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
        <Card>
          <RuleForm kind="tailoring_note" autoFocus={reverted} key={String(reverted)} />
        </Card>
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
