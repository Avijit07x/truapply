import { useState } from "react";
import { useRunStart } from "../../api/mutations";
import type { RunLimits } from "../../api/types";
import { Note, Row } from "../../ui/Blocks";
import { Button } from "../../ui/Button";
import { Checkbox, TextField } from "../../ui/Fields";
import { Play } from "../../ui/icons";
import { toast } from "../../ui/toasts";
import styles from "./Runs.module.css";

export function RunForm({ limits }: { limits: RunLimits }) {
  const start = useRunStart();
  const [limit, setLimit] = useState(String(limits.default));
  const [search, setSearch] = useState(true);
  const count = Number(limit);
  const valid = Number.isInteger(count) && count >= limits.min && count <= limits.max;
  const run = () => {
    start.mutate(
      { limit: count, search },
      {
        onSuccess: () => {
          toast("Run started. Nothing is sent.");
        },
      },
    );
  };
  return (
    <section className={styles.card} aria-labelledby="start-title">
      <h2 id="start-title" className={styles.blockTitle}>
        Start a run
      </h2>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          run();
        }}
      >
        <div className={styles.form}>
          <div className={styles.limit}>
            <TextField
              label="How many jobs"
              hint={`From ${String(limits.min)} to ${String(limits.max)}.`}
              type="number"
              min={limits.min}
              max={limits.max}
              required
              value={limit}
              onChange={setLimit}
            />
          </div>
          <div className={styles.formSide}>
            <Checkbox label="Search for new jobs first" checked={search} onChange={setSearch} />
            <Note>It finds, scores and tailors. You apply yourself in your Chrome.</Note>
            <Row>
              <Button
                type="submit"
                variant="primary"
                icon={<Play />}
                busy={start.isPending}
                disabled={!valid}
              >
                Run now
              </Button>
            </Row>
          </div>
        </div>
      </form>
    </section>
  );
}
