import { Toggle } from "@base-ui/react/toggle";
import { ToggleGroup } from "@base-ui/react/toggle-group";
import { useState } from "react";
import { type JobChange, useJobChange } from "../../api/mutations";
import type { Action, JobDetail } from "../../api/types";
import { DismissForm } from "../../components/DismissForm";
import { Row } from "../../ui/Blocks";
import { Button } from "../../ui/Button";
import { Callout } from "../../ui/Callout";
import { Dialog } from "../../ui/Dialog";
import { ExternalLink } from "../../ui/ExternalLink";
import { Check, Close } from "../../ui/icons";
import { toast } from "../../ui/toasts";
import styles from "./Job.module.css";

const FINISH_HINT =
  "Filled in, but the site wants you to prove you're human. Open the form in your own browser, check the answers below, and submit.";

function MatchFeedback({ job }: { job: JobDetail }) {
  const change = useJobChange(job.id);
  return (
    <div className={styles.feedback}>
      <span className={styles.feedbackLabel}>Was this a good match for you?</span>
      <ToggleGroup
        className={styles.toggles}
        value={job.feedback === 0 ? [] : [String(job.feedback)]}
        disabled={change.isPending}
        onValueChange={(value) => {
          const picked = value[0];
          if (picked) {
            change.mutate({ action: "thumbs", body: { value: Number(picked) } });
          }
        }}
      >
        <Toggle value="1" className={styles.toggle}>
          Good match
        </Toggle>
        <Toggle value="-1" className={styles.toggle}>
          Bad match
        </Toggle>
      </ToggleGroup>
    </div>
  );
}

export function JobActions({ job }: { job: JobDetail }) {
  const change = useJobChange(job.id);
  const [dismissing, setDismissing] = useState(false);
  const can = (action: Action) => job.actions.includes(action);
  const hasButtons = can("approve") || can("finished") || can("dismiss");
  const act = (next: JobChange, done: string) => {
    change.mutate(next, {
      onSuccess: () => {
        toast(done);
      },
    });
  };
  return (
    <section className={styles.actions} aria-label="What you can do">
      {can("finished") && <Callout>{FINISH_HINT}</Callout>}
      {hasButtons && (
        <Row>
          {can("approve") && (
            <Button
              variant="primary"
              icon={<Check />}
              busy={change.isPending}
              onClick={() => {
                act(
                  { action: "approve" },
                  "Approved. It's sent on the next run where you choose to send.",
                );
              }}
            >
              Approve
            </Button>
          )}
          {can("finished") && job.applyUrl && (
            <ExternalLink href={job.applyUrl} asButton>
              Open the form
            </ExternalLink>
          )}
          {can("finished") && (
            <Button
              variant="primary"
              busy={change.isPending}
              onClick={() => {
                act({ action: "finished" }, "Marked as applied.");
              }}
            >
              I submitted it
            </Button>
          )}
          {can("dismiss") && (
            <Button
              variant="danger"
              icon={<Close size={12} />}
              onClick={() => {
                setDismissing(true);
              }}
            >
              Dismiss
            </Button>
          )}
        </Row>
      )}
      {can("thumbs") && <MatchFeedback job={job} />}
      <Dialog
        open={dismissing}
        title="Dismiss this job?"
        onClose={() => {
          setDismissing(false);
        }}
      >
        <DismissForm
          reasons={job.dismissReasons}
          busy={change.isPending}
          onCancel={() => {
            setDismissing(false);
          }}
          onDismiss={(reason) => {
            act({ action: "dismiss", body: { reason } }, "Dismissed.");
            setDismissing(false);
          }}
        />
      </Dialog>
    </section>
  );
}
