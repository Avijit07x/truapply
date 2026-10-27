import { useSuspenseQueries } from "@tanstack/react-query";
import { queries } from "../../api/queries";
import { RuleForm } from "../../components/RuleForm";
import { plural } from "../../lib/format";
import { cx } from "../../lib/cx";
import { Link } from "../../lib/router";
import styles from "./Home.module.css";
import { HomeHeader } from "./HomeHeader";
import { NeedsYou } from "./NeedsYou";
import { Pipeline } from "./Pipeline";
import { Recent } from "./Recent";

export default function HomePage() {
  const [{ data: summary }, { data: board }, { data: workflow }] = useSuspenseQueries({
    queries: [queries.summary(), queries.board(), queries.workflow()],
  });
  return (
    <div className={styles.page}>
      <HomeHeader summary={summary} />
      <div className={styles.layout}>
        <div className={styles.main}>
          <NeedsYou columns={board.columns} />
          <Recent columns={board.columns} />
        </div>
        <aside className={styles.rail} aria-label="How it's going">
          <Pipeline groups={workflow.groups} />
          <section className={cx(styles.railSection, styles.tell)}>
            <RuleForm kind="rule" compact />
            {summary.suggestions > 0 && (
              <Link to="/learned" className={styles.railLink}>
                {plural(summary.suggestions, "suggestion")} to review
              </Link>
            )}
          </section>
        </aside>
      </div>
    </div>
  );
}
