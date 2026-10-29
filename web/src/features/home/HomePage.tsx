import { useSuspenseQueries } from "@tanstack/react-query";
import { queries } from "../../api/queries";
import { plural } from "../../lib/format";
import { Link } from "../../lib/router";
import { ArrowRight, Spark } from "../../ui/icons";
import styles from "./Home.module.css";
import { NeedsYou } from "./NeedsYou";
import { Pipeline } from "./Pipeline";
import { Recent } from "./Recent";

const TODAY = new Intl.DateTimeFormat(undefined, {
  weekday: "long",
  day: "numeric",
  month: "long",
});

function headline(count: number): string {
  if (count === 0) {
    return "You're all caught up";
  }
  return count === 1 ? "1 job is ready for you" : `${plural(count, "job")} are ready for you`;
}

export default function HomePage() {
  const [{ data: summary }, { data: board }, { data: workflow }] = useSuspenseQueries({
    queries: [queries.summary(), queries.board(), queries.workflow()],
  });
  return (
    <div className={styles.page}>
      <header className={styles.hello}>
        <div>
          <p className={styles.date}>{TODAY.format(new Date())}</p>
          <h1 className={styles.title}>{headline(summary.counts.ready ?? 0)}</h1>
        </div>
        <Link to="/jobs" className={styles.link}>
          All jobs
          <ArrowRight size={12} />
        </Link>
      </header>
      {summary.suggestions > 0 && (
        <Link to="/learned" className={styles.suggest}>
          <Spark size={14} />
          {plural(summary.suggestions, "suggestion")} from jobs you dismissed. Review them
          <ArrowRight size={12} />
        </Link>
      )}
      <NeedsYou columns={board.columns} />
      <Pipeline groups={workflow.groups} />
      <Recent columns={board.columns} />
    </div>
  );
}
