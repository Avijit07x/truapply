import { type ReactNode, useState } from "react";
import { Row } from "../../ui/Blocks";
import { Button } from "../../ui/Button";
import { TextField } from "../../ui/Fields";
import styles from "./Learned.module.css";

type EditableProps = {
  heading?: ReactNode;
  label: ReactNode;
  value: string;
  limit: number;
  busy: boolean;
  onSave: (text: string, done: () => void) => void;
  onDelete: () => void;
};

export function Editable({ heading, label, value, limit, busy, onSave, onDelete }: EditableProps) {
  const [draft, setDraft] = useState<string | null>(null);
  if (draft === null) {
    return (
      <div className={styles.item}>
        <div className={styles.body}>
          {heading}
          <p className={styles.text}>{value}</p>
        </div>
        <Row>
          <Button
            variant="ghost"
            onClick={() => {
              setDraft(value);
            }}
          >
            Edit
          </Button>
          <Button variant="ghost" busy={busy} onClick={onDelete}>
            Delete
          </Button>
        </Row>
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
