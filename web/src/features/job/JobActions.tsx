import { useState } from "react";
import { useJobChange } from "../../api/mutations";
import type { JobDetail } from "../../api/types";
import { DismissForm } from "../../components/DismissForm";
import { Row } from "../../ui/Blocks";
import { Button } from "../../ui/Button";
import { Dialog } from "../../ui/Dialog";
import { ExternalLink } from "../../ui/ExternalLink";
import { Check, Close, Spark } from "../../ui/icons";
import { toast } from "../../ui/toasts";

function applyLink(job: JobDetail): string | null {
  return job.status === "ready" || job.status === "scored" ? (job.applyUrl ?? job.url) : null;
}

export function JobActions({ job }: { job: JobDetail }) {
  const change = useJobChange(job.id);
  const [dismissing, setDismissing] = useState(false);
  const canDismiss = job.actions.includes("dismiss");
  const canFinish = job.actions.includes("finished");
  const canScore = job.actions.includes("score");
  const link = applyLink(job);
  if (!canDismiss && !canFinish && !canScore && !link) {
    return null;
  }
  const close = () => {
    setDismissing(false);
  };
  return (
    <Row>
      {canDismiss && (
        <Button
          variant="dangerSoft"
          icon={<Close size={12} />}
          onClick={() => {
            setDismissing(true);
          }}
        >
          Dismiss
        </Button>
      )}
      {canScore && (
        <Button
          icon={<Spark />}
          busy={change.isPending}
          onClick={() => {
            change.mutate(
              { action: "score" },
              {
                onSuccess: () => {
                  toast("Scoring it now. The score shows here in about a minute.");
                },
              },
            );
          }}
        >
          Score this
        </Button>
      )}
      {canFinish && (
        <Button
          icon={<Check />}
          busy={change.isPending}
          onClick={() => {
            change.mutate(
              { action: "finished" },
              {
                onSuccess: () => {
                  toast("Marked as applied.");
                },
              },
            );
          }}
        >
          I submitted it
        </Button>
      )}
      {link && (
        <ExternalLink href={link} button="primary">
          Open in my Chrome
        </ExternalLink>
      )}
      <Dialog open={dismissing} title="Dismiss this job?" onClose={close}>
        <DismissForm
          reasons={job.dismissReasons}
          busy={change.isPending}
          onCancel={close}
          onDismiss={(reason) => {
            change.mutate(
              { action: "dismiss", body: { reason } },
              {
                onSuccess: () => {
                  toast("Dismissed.");
                },
              },
            );
            close();
          }}
        />
      </Dialog>
    </Row>
  );
}
