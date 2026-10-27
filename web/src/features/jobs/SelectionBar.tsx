import { useState } from "react";
import { useDismissMany, useScoreMany } from "../../api/mutations";
import type { Dismissed } from "../../api/types";
import { DismissForm } from "../../components/DismissForm";
import { plural } from "../../lib/format";
import { Button } from "../../ui/Button";
import { Dialog } from "../../ui/Dialog";
import { toast } from "../../ui/toasts";
import styles from "./Jobs.module.css";

function outcome({ dismissed, skipped }: Dismissed): string {
  const done = `Dismissed ${plural(dismissed, "job")}.`;
  return skipped > 0 ? `${done} Left ${plural(skipped, "job")} alone that had moved on.` : done;
}

type SelectionBarProps = {
  ids: readonly number[];
  reasons: readonly string[];
  onClear: () => void;
};

export function SelectionBar({ ids, reasons, onClear }: SelectionBarProps) {
  const [asking, setAsking] = useState(false);
  const dismiss = useDismissMany();
  const score = useScoreMany();
  if (ids.length === 0) {
    return null;
  }
  const close = () => {
    setAsking(false);
  };
  return (
    <>
      <div className={styles.selectionBar} role="toolbar" aria-label="Selected jobs">
        <span className={styles.selectionCount}>{plural(ids.length, "job")} selected</span>
        <Button
          busy={score.isPending}
          onClick={() => {
            score.mutate(ids, {
              onSuccess: ({ scoring, skipped }) => {
                const left = skipped
                  ? ` ${plural(skipped, "job")} left alone: only new or skipped jobs get scored.`
                  : "";
                toast(
                  scoring
                    ? `Scoring ${plural(scoring, "job")} now. Scores show up in a minute or two.${left}`
                    : `Nothing to score.${left}`,
                );
                onClear();
              },
            });
          }}
        >
          Score these
        </Button>
        <Button
          variant="danger"
          onClick={() => {
            setAsking(true);
          }}
        >
          Dismiss
        </Button>
        <Button variant="ghost" onClick={onClear}>
          Clear
        </Button>
      </div>
      <Dialog open={asking} title={`Dismiss ${plural(ids.length, "job")}?`} onClose={close}>
        <DismissForm
          reasons={reasons}
          busy={dismiss.isPending}
          onCancel={close}
          onDismiss={(reason) => {
            dismiss.mutate(
              { ids: [...ids], reason },
              {
                onSuccess: (result) => {
                  toast(outcome(result));
                  close();
                  onClear();
                },
              },
            );
          }}
        />
      </Dialog>
    </>
  );
}
