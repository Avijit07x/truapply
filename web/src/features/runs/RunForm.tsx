import { useState } from "react";
import { useRunStart } from "../../api/mutations";
import type { RunLimits } from "../../api/types";
import { Card, Note, Row, Stack } from "../../ui/Blocks";
import { Button } from "../../ui/Button";
import { Dialog } from "../../ui/Dialog";
import { Checkbox, TextField } from "../../ui/Fields";
import { Play } from "../../ui/icons";
import { toast } from "../../ui/toasts";
import styles from "./Runs.module.css";

export function RunForm({ limits }: { limits: RunLimits }) {
  const start = useRunStart();
  const [limit, setLimit] = useState(String(limits.default));
  const [search, setSearch] = useState(true);
  const [send, setSend] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const count = Number(limit);
  const valid = Number.isInteger(count) && count >= limits.min && count <= limits.max;
  const close = () => {
    setConfirming(false);
  };
  const run = () => {
    start.mutate(
      { limit: count, search, send },
      {
        onSuccess: () => {
          close();
          toast(send ? "Run started. Approved jobs are sent." : "Run started. Nothing is sent.");
        },
      },
    );
  };
  return (
    <Card title="Start a run">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (send) {
            setConfirming(true);
          } else {
            run();
          }
        }}
      >
        <Stack>
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
          <Checkbox label="Search for new jobs first" checked={search} onChange={setSearch} />
          <Checkbox label="Really send the jobs I approved" checked={send} onChange={setSend} />
          <Note>
            {send
              ? "Approved jobs are sent to the employers."
              : "Dry run: forms are filled in, nothing is sent."}
          </Note>
          <Row>
            <Button
              type="submit"
              variant="primary"
              icon={<Play />}
              busy={start.isPending && !confirming}
              disabled={!valid}
            >
              {send ? "Run and send" : "Run now"}
            </Button>
          </Row>
        </Stack>
      </form>
      <Dialog open={confirming} title="Send real applications?" onClose={close}>
        <Note>The jobs you approved are sent to the employers. This can't be undone.</Note>
        <Row>
          <Button variant="primary" busy={start.isPending} onClick={run}>
            Run and send
          </Button>
          <Button variant="ghost" onClick={close}>
            Cancel
          </Button>
        </Row>
      </Dialog>
    </Card>
  );
}
