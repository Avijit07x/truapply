import { useSuspenseQueries } from "@tanstack/react-query";
import { queries } from "../../api/queries";
import { RuleForm } from "../../components/RuleForm";
import { plural } from "../../lib/format";
import { Link } from "../../lib/router";
import { Card, Note } from "../../ui/Blocks";
import styles from "./Home.module.css";
import { Hero } from "./Hero";
import { NeedsYou } from "./NeedsYou";
import { Pipeline } from "./Pipeline";
import { Stats } from "./Stats";
import { TrustCard } from "./TrustCard";

export default function HomePage() {
  const [{ data: summary }, { data: board }, { data: workflow }] = useSuspenseQueries({
    queries: [queries.summary(), queries.board(), queries.workflow()],
  });
  return (
    <div className={styles.page}>
      <Hero summary={summary} />
      <Stats counts={summary.counts} />
      <div className={styles.columns}>
        <div className={styles.stack}>
          <NeedsYou columns={board.columns} />
          <Card>
            <RuleForm kind="rule" />
            {summary.suggestions > 0 && (
              <Note>
                <Link to="/learned">{plural(summary.suggestions, "suggestion")} to review</Link>
              </Note>
            )}
          </Card>
        </div>
        <div className={styles.stack}>
          <Pipeline groups={workflow.groups} />
          <TrustCard trust={summary.trust} />
        </div>
      </div>
    </div>
  );
}
