import { useSendReady } from "../../api/mutations";
import type { Column, SendQueued } from "../../api/types";
import { plural } from "../../lib/format";
import { Link } from "../../lib/router";
import { Row } from "../../ui/Blocks";
import { Button } from "../../ui/Button";
import { ArrowRight, Check, Send } from "../../ui/icons";
import { toast } from "../../ui/toasts";
import styles from "./Home.module.css";
import { QueueItem } from "./QueueItem";

const WAKE_EXTENSION = "truapply:send";

function sentNote({ queued, below, score }: SendQueued): string {
  const kept = below ? ` ${plural(below, "job")} under ${String(score)} stay for you.` : "";
  if (!queued) return `Nothing to send: none of them scores ${String(score)} or more.${kept}`;
  return `Sending ${plural(queued, "job")}, one tab at a time in your Chrome.${kept}`;
}

function SendThese() {
  const send = useSendReady();
  return (
    <Row>
      <Button
        icon={<Send size={14} />}
        busy={send.isPending}
        onClick={() => {
          send.mutate(undefined, {
            onSuccess: (result) => {
              window.postMessage(WAKE_EXTENSION, window.location.origin);
              toast(sentNote(result));
            },
          });
        }}
      >
        Send these with auto-submit
      </Button>
    </Row>
  );
}

export function NeedsYou({ columns }: { columns: readonly Column[] }) {
  const ready = columns.find((column) => column.status === "ready");
  const total = ready?.total ?? 0;
  return (
    <section className={styles.needs} aria-labelledby="needs-title">
      <header className={styles.railHead}>
        <h2 id="needs-title" className={styles.railTitle}>
          Ready for you to apply
        </h2>
        <span className={styles.railMeta}>{total.toLocaleString()}</span>
      </header>
      {ready && total > 0 ? (
        <>
          <p className={styles.hint}>
            Open one in your Chrome. The TruApply extension fills it in; you check it and press
            Submit.
          </p>
          <SendThese />
          <ul className={styles.queue}>
            {ready.jobs.map((job) => (
              <QueueItem key={job.id} job={job} />
            ))}
          </ul>
          {total > ready.jobs.length && (
            <Link to="/jobs?status=ready" className={styles.more}>
              See all {total.toLocaleString()}
              <ArrowRight size={12} />
            </Link>
          )}
        </>
      ) : (
        <p className={styles.calm}>
          <Check size={14} />
          Nothing ready yet. New ones show up after a run.
        </p>
      )}
    </section>
  );
}
