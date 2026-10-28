import { Popover } from "@base-ui/react/popover";
import { useState } from "react";
import { useAddNames } from "../../api/mutations";
import type { Named } from "../../api/types";
import { plural } from "../../lib/format";
import { Row } from "../../ui/Blocks";
import { Button } from "../../ui/Button";
import { TextField } from "../../ui/Fields";
import { Plus } from "../../ui/icons";
import { toast } from "../../ui/toasts";
import styles from "../jobs/Jobs.module.css";

function outcome({ added, known, missing, jobs }: Named): string {
  const parts: string[] = [];
  if (added.length > 0) {
    parts.push(`Added ${added.join(", ")}, with ${plural(jobs, "new job")} for you.`);
  }
  if (known.length > 0) parts.push(`Already checked: ${known.join(", ")}.`);
  if (missing.length > 0) {
    parts.push(`Not found with jobs in your country: ${missing.join(", ")}.`);
  }
  return parts.join(" ");
}

export function AddNames() {
  const [open, setOpen] = useState(false);
  const [names, setNames] = useState("");
  const add = useAddNames();
  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger render={<Button icon={<Plus size={14} />} />}>Add companies</Popover.Trigger>
      <Popover.Portal>
        <Popover.Positioner className={styles.positioner} sideOffset={6} align="end">
          <Popover.Popup className={styles.linkPopup}>
            <Popover.Title className={styles.popupTitle}>Add companies</Popover.Title>
            <form
              className={styles.linkForm}
              onSubmit={(event) => {
                event.preventDefault();
                add.mutate(names.trim(), {
                  onSuccess: (result) => {
                    toast(outcome(result));
                    setNames("");
                    setOpen(false);
                  },
                });
              }}
            >
              <TextField
                label="Company names or websites, one per line"
                placeholder={"Zinier\nglance.com"}
                multiline
                rows={5}
                autoFocus
                value={names}
                onChange={setNames}
              />
              <p className={styles.linkHint}>
                Each is looked up on Greenhouse, Lever and Ashby, and added only if it has jobs in
                your country. Up to 50 at a time.
              </p>
              <Row>
                <Button
                  type="submit"
                  variant="primary"
                  busy={add.isPending}
                  disabled={!names.trim()}
                >
                  Add
                </Button>
              </Row>
            </form>
          </Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
    </Popover.Root>
  );
}
