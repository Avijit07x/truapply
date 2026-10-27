import { Popover } from "@base-ui/react/popover";
import { useState } from "react";
import { useAddLink } from "../../api/mutations";
import type { Linked } from "../../api/types";
import { plural } from "../../lib/format";
import { Row } from "../../ui/Blocks";
import { Button } from "../../ui/Button";
import { TextField } from "../../ui/Fields";
import { Plus } from "../../ui/icons";
import { toast } from "../../ui/toasts";
import styles from "./Jobs.module.css";

function outcome({ company, open, kept, added }: Linked): string {
  if (added > 0) {
    return `Added ${company}: ${plural(added, "new job")} for you. Press Run now to score and fill it.`;
  }
  if (kept > 0) {
    return `${company} is checked on every run now. Its jobs for you are already in your list.`;
  }
  return `${company} is checked on every run now. None of its ${String(open)} open jobs fit your titles and places yet.`;
}

export function AddLink() {
  const [open, setOpen] = useState(false);
  const [link, setLink] = useState("");
  const add = useAddLink();
  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger render={<Button icon={<Plus size={14} />} />}>
        Add a job link
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Positioner className={styles.positioner} sideOffset={6} align="end">
          <Popover.Popup className={styles.linkPopup}>
            <Popover.Title className={styles.popupTitle}>Add a job link</Popover.Title>
            <form
              className={styles.linkForm}
              onSubmit={(event) => {
                event.preventDefault();
                add.mutate(link.trim(), {
                  onSuccess: (result) => {
                    toast(outcome(result));
                    setLink("");
                    setOpen(false);
                  },
                });
              }}
            >
              <TextField
                label="A Greenhouse, Lever or Ashby job or careers link"
                placeholder="https://job-boards.greenhouse.io/..."
                autoFocus
                value={link}
                onChange={setLink}
              />
              <p className={styles.linkHint}>
                That company's jobs are checked now and on every run after this.
              </p>
              <Row>
                <Button
                  type="submit"
                  variant="primary"
                  busy={add.isPending}
                  disabled={!link.trim()}
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
