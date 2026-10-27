import { type ReactNode, useState } from "react";
import { cx } from "../../lib/cx";
import { Row } from "../../ui/Blocks";
import { Button, IconButton } from "../../ui/Button";
import { TextField } from "../../ui/Fields";
import { Pencil, Trash } from "../../ui/icons";
import styles from "./Learned.module.css";

const LONG = 220;

type EditableProps = {
  heading?: ReactNode;
  compact?: boolean;
  label: string;
  name: string;
  value: string;
  limit: number;
  busy: boolean;
  onSave: (text: string, done: () => void) => void;
  onDelete: () => void;
};

export function Editable({
  heading,
  compact = false,
  label,
  name,
  value,
  limit,
  busy,
  onSave,
  onDelete,
}: EditableProps) {
  const [draft, setDraft] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  if (draft === null) {
    const long = value.length > LONG;
    return (
      <div className={cx(styles.item, heading ? compact && styles.compact : styles.plain)}>
        {heading && <div className={styles.head}>{heading}</div>}
        <div className={styles.value}>
          <p className={cx(styles.text, long && !open && styles.clamped)}>{value}</p>
          {long && (
            <button
              type="button"
              className={styles.more}
              aria-expanded={open}
              onClick={() => {
                setOpen(!open);
              }}
            >
              {open ? "Show less" : "Show all"}
            </button>
          )}
        </div>
        <div className={styles.tools}>
          <IconButton
            label={`Edit ${name}`}
            title="Edit"
            onClick={() => {
              setDraft(value);
            }}
          >
            <Pencil size={14} />
          </IconButton>
          <IconButton label={`Delete ${name}`} title="Delete" disabled={busy} onClick={onDelete}>
            <Trash size={14} />
          </IconButton>
        </div>
      </div>
    );
  }
  const text = draft.trim();
  const close = () => {
    setDraft(null);
  };
  return (
    <form
      className={styles.editing}
      onSubmit={(event) => {
        event.preventDefault();
        onSave(text, close);
      }}
    >
      <TextField
        label={label}
        multiline
        rows={2}
        maxLength={limit}
        required
        autoFocus
        value={draft}
        onChange={setDraft}
      />
      <Row>
        <Button type="submit" variant="primary" busy={busy} disabled={!text || text === value}>
          Save
        </Button>
        <Button variant="ghost" onClick={close}>
          Cancel
        </Button>
      </Row>
    </form>
  );
}
