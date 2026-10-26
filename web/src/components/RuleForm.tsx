import { useState } from "react";
import { learnedPaths, useLearnedChange } from "../api/mutations";
import type { RuleKind } from "../api/types";
import { Row, Stack } from "../ui/Blocks";
import { Button } from "../ui/Button";
import { TextField } from "../ui/Fields";
import { toast } from "../ui/toasts";

export const RULE_LIMIT = 300;

const COPY: Record<RuleKind, { label: string; hint: string; button: string; saved: string }> = {
  rule: {
    label: "Tell SatyaApply",
    hint: "Plain words, like “no staffing agencies” or “Pune is fine, Mumbai is not”. It changes how jobs are scored. It can't add facts to your resume.",
    button: "Add rule",
    saved: "Rule added. It's used from the next run.",
  },
  tailoring_note: {
    label: "Tailoring note",
    hint: "How should your resume be tailored next time? For example: don't change my headline.",
    button: "Save note",
    saved: "Note saved. It's used the next time a resume is tailored.",
  },
};

type RuleFormProps = { kind: RuleKind; autoFocus?: boolean };

export function RuleForm({ kind, autoFocus = false }: RuleFormProps) {
  const [text, setText] = useState("");
  const change = useLearnedChange();
  const copy = COPY[kind];
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        change.mutate([learnedPaths.add, { kind, text }], {
          onSuccess: () => {
            setText("");
            toast(copy.saved);
          },
        });
      }}
    >
      <Stack>
        <TextField
          label={copy.label}
          hint={copy.hint}
          multiline
          rows={2}
          maxLength={RULE_LIMIT}
          required
          autoFocus={autoFocus}
          value={text}
          onChange={setText}
        />
        <Row>
          <Button type="submit" variant="primary" busy={change.isPending} disabled={!text.trim()}>
            {copy.button}
          </Button>
        </Row>
      </Stack>
    </form>
  );
}
