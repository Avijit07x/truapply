import type { JobDetail } from "../../api/types";
import { CopyButton } from "../../components/CopyButton";
import styles from "./Job.module.css";
import { Panel } from "./Panel";

export function FilledAnswers({ job }: { job: JobDetail }) {
  if (job.sent.length === 0) {
    return null;
  }
  return (
    <Panel title="What you sent">
      <dl className={styles.answers}>
        {job.sent.map((item, index) => (
          <div key={`${String(index)}-${item.question}`} className={styles.answer}>
            <dt>{item.question}</dt>
            <dd>{item.answer}</dd>
            <CopyButton text={item.answer} label={`Copy the answer to “${item.question}”`} />
          </div>
        ))}
      </dl>
    </Panel>
  );
}
