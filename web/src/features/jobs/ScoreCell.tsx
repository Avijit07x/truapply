import { createContext, use, useState } from "react";
import { useScoreMany } from "../../api/mutations";
import type { JobRow, Status } from "../../api/types";
import { Score } from "../../components/JobList";
import { Spark } from "../../ui/icons";
import { toast } from "../../ui/toasts";
import { Spinner } from "../../ui/Spinner";
import styles from "./Jobs.module.css";

type Scoring = { scorable: ReadonlySet<Status>; scoring: ReadonlySet<number> };

export const ScoringContext = createContext<Scoring>({ scorable: new Set(), scoring: new Set() });

export function ScoreCell({ job }: { job: JobRow }) {
  const { scorable, scoring } = use(ScoringContext);
  const ask = useScoreMany();
  const [asked, setAsked] = useState(false);
  if (scoring.has(job.id) || (asked && ask.isPending)) {
    return (
      <span className={styles.scoring} role="status">
        <Spinner />
        Scoring
      </span>
    );
  }
  if (job.score !== null || !scorable.has(job.status)) {
    return <Score value={job.score} />;
  }
  return (
    <button
      type="button"
      className={styles.scoreButton}
      aria-label={`Score ${job.title} at ${job.company}`}
      onClick={() => {
        setAsked(true);
        ask.mutate([job.id], {
          onError: () => {
            toast("Couldn't start scoring. Is the app still running?");
          },
        });
      }}
    >
      <Spark size={11} />
      Score
    </button>
  );
}
