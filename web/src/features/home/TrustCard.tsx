import { Meter } from "@base-ui/react/meter";
import { useAutoSubmit } from "../../api/mutations";
import type { Trust } from "../../api/types";
import { plural } from "../../lib/format";
import { Card, Note, Row } from "../../ui/Blocks";
import { Button } from "../../ui/Button";
import { toast } from "../../ui/toasts";
import styles from "./Home.module.css";

const FULL = 100;

function progress(trust: Trust): string {
  if (trust.autoSubmit) {
    return `On. Strong matches (score ${String(trust.autoSubmitScore)} or more) are sent for you.`;
  }
  const left = trust.offerAt - trust.count;
  return left > 0
    ? `${plural(left, "more clean approval")} in a row to unlock it.`
    : "Earned. You can turn it on.";
}

export function TrustCard({ trust }: { trust: Trust }) {
  const change = useAutoSubmit();
  const earned = trust.count >= trust.offerAt;
  const done = Math.min(trust.count, trust.offerAt);
  const toggle = (on: boolean) => {
    change.mutate(on, {
      onSuccess: () => {
        toast(on ? "Auto-submit is on." : "Auto-submit is off. Every job waits for your OK.");
      },
    });
  };
  return (
    <Card title="Auto-submit">
      <div className={styles.trust}>
        <Meter.Root
          className={styles.ring}
          value={done}
          max={trust.offerAt}
          aria-label="Clean approvals in a row"
          aria-valuetext={`${String(trust.count)} of ${String(trust.offerAt)} clean approvals`}
        >
          <svg viewBox="0 0 64 64" aria-hidden="true">
            <circle className={styles.ringTrack} cx="32" cy="32" r="27" pathLength={FULL} />
            {done > 0 && (
              <circle
                className={styles.ringFill}
                cx="32"
                cy="32"
                r="27"
                pathLength={FULL}
                style={{ strokeDashoffset: FULL - (done / trust.offerAt) * FULL }}
              />
            )}
          </svg>
          <span className={styles.ringValue}>
            {trust.count}
            <small>/{trust.offerAt}</small>
          </span>
        </Meter.Root>
        <div className={styles.trustText}>
          <p>{progress(trust)}</p>
          <Note>Turns itself off after 2 bad matches in the last 10 it sent.</Note>
        </div>
      </div>
      {(trust.autoSubmit || earned) && (
        <Row>
          {trust.autoSubmit ? (
            <Button
              busy={change.isPending}
              onClick={() => {
                toggle(false);
              }}
            >
              Turn off
            </Button>
          ) : (
            <Button
              variant="primary"
              busy={change.isPending}
              onClick={() => {
                toggle(true);
              }}
            >
              Turn on auto-submit
            </Button>
          )}
        </Row>
      )}
    </Card>
  );
}
