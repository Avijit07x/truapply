import { useState } from "react";
import { Row } from "../ui/Blocks";
import { Button } from "../ui/Button";
import { SelectField } from "../ui/Fields";

type DismissFormProps = {
  reasons: readonly string[];
  busy: boolean;
  onDismiss: (reason: string) => void;
  onCancel?: () => void;
};

export function DismissForm({ reasons, busy, onDismiss, onCancel }: DismissFormProps) {
  const [reason, setReason] = useState(reasons[0] ?? "other");
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        onDismiss(reason);
      }}
    >
      <Row align="end">
        <SelectField label="Why not" value={reason} options={reasons} onChange={setReason} />
        <Button type="submit" variant="danger" busy={busy}>
          Dismiss
        </Button>
        {onCancel && (
          <Button variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        )}
      </Row>
    </form>
  );
}
