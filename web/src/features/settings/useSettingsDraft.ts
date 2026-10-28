import { useState } from "react";
import { RequestFailed } from "../../api/client";
import { useSaveSettings } from "../../api/mutations";
import type { SettingsView } from "../../api/types";
import { type Draft, toDraft, toValues } from "./draft";

export function useSettingsDraft(view: SettingsView, onSaved: () => void) {
  const save = useSaveSettings();
  const saved = toDraft(view.values);
  const [edits, setEdits] = useState<Draft | null>(null);
  const draft = edits ?? saved;
  const dirty = edits !== null && JSON.stringify(edits) !== JSON.stringify(saved);
  const set =
    <Name extends keyof Draft>(name: Name) =>
    (value: Draft[Name]) => {
      setEdits((current) => ({ ...(current ?? saved), [name]: value }));
    };
  return {
    group: { draft, set, limits: view.limits },
    dirty,
    saving: save.isPending,
    problems: save.error instanceof RequestFailed ? save.error.problems : [],
    submit: () => {
      save.mutate(toValues(draft), {
        onSuccess: () => {
          setEdits(null);
          onSaved();
        },
      });
    },
    undo: () => {
      setEdits(null);
      save.reset();
    },
  };
}
