import { useSuspenseQuery } from "@tanstack/react-query";
import { useState } from "react";
import { RequestFailed } from "../../api/client";
import { useSaveSettings } from "../../api/mutations";
import { queries } from "../../api/queries";
import type { SettingsValues, SettingsView } from "../../api/types";
import { Note, PageHeader, Row, Section, Stack } from "../../ui/Blocks";
import { Button } from "../../ui/Button";
import { Callout } from "../../ui/Callout";
import { Checkbox, TagsField, TextField } from "../../ui/Fields";
import { toast } from "../../ui/toasts";
import styles from "./Settings.module.css";

type NumberName = "maxJobAgeDays" | "minScore" | "expectedMin" | "expectedMax" | "dailyCap";
type Draft = Omit<SettingsValues, NumberName> & Record<NumberName, string>;

function text(value: number | null): string {
  return value === null ? "" : String(value);
}

function whole(value: string): number {
  return value.trim() ? Number(value) : Number.NaN;
}

function toDraft(values: SettingsValues): Draft {
  return {
    ...values,
    maxJobAgeDays: text(values.maxJobAgeDays),
    minScore: text(values.minScore),
    expectedMin: text(values.expectedMin),
    expectedMax: text(values.expectedMax),
    dailyCap: text(values.dailyCap),
  };
}

function toValues(draft: Draft): SettingsValues {
  return {
    ...draft,
    maxJobAgeDays: whole(draft.maxJobAgeDays),
    minScore: whole(draft.minScore),
    expectedMin: whole(draft.expectedMin),
    expectedMax: whole(draft.expectedMax),
    dailyCap: draft.dailyCap.trim() ? Number(draft.dailyCap) : null,
  };
}

function SettingsForm({ view }: { view: SettingsView }) {
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
  const { fixed } = view;
  const list = { maxItems: fixed.maxItems, maxLength: fixed.maxText };
  const problems = save.error instanceof RequestFailed ? save.error.problems : [];
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        save.mutate(toValues(draft), {
          onSuccess: () => {
            setEdits(null);
            toast("Settings saved. They're used from the next run.");
          },
        });
      }}
    >
      <Section title="Job search">
        <Stack>
          <Note>
            Which jobs to look for. Jobs scoring below the minimum match score are skipped.
          </Note>
          <TagsField
            label="Title keywords"
            values={draft.titleKeywords}
            onChange={set("titleKeywords")}
            {...list}
          />
          <TagsField
            label="Titles to skip"
            values={draft.titleExclude}
            onChange={set("titleExclude")}
            {...list}
          />
          <TagsField
            label="Companies to skip"
            values={draft.skipCompanies}
            onChange={set("skipCompanies")}
            {...list}
          />
          <div className={styles.pair}>
            <TextField
              label="Oldest job to consider, in days"
              type="number"
              min={1}
              max={fixed.maxJobAgeDays}
              required
              value={draft.maxJobAgeDays}
              onChange={set("maxJobAgeDays")}
            />
            <TextField
              label="Minimum match score"
              hint={`0 to ${String(fixed.strongScore)}.`}
              type="number"
              min={0}
              max={fixed.strongScore}
              required
              value={draft.minScore}
              onChange={set("minScore")}
            />
          </div>
        </Stack>
      </Section>
      <Section title="Where you'll work">
        <Stack>
          <Note>
            Tick every kind of place you're happy to work. Jobs anywhere else are skipped.
          </Note>
          <Checkbox
            label={`On-site or hybrid in ${fixed.city}`}
            checked={draft.onsiteCity}
            onChange={set("onsiteCity")}
          />
          <Checkbox
            label={`Remote in ${fixed.country}`}
            checked={draft.remoteCountry}
            onChange={set("remoteCountry")}
          />
          <Checkbox
            label={`Moving to another city in ${fixed.country}`}
            checked={draft.relocate}
            onChange={set("relocate")}
          />
          {draft.relocate && (
            <TagsField
              label="Cities you'd move to"
              values={draft.relocateCities}
              onChange={set("relocateCities")}
              {...list}
            />
          )}
          <Checkbox
            label="Remote for companies abroad"
            checked={draft.remoteAbroad}
            onChange={set("remoteAbroad")}
          />
        </Stack>
      </Section>
      <Section title="Pay and notice">
        <Stack>
          <Note>
            Used to answer pay and notice questions on forms. The currency ({fixed.currency}) is set
            in setup.
          </Note>
          <div className={styles.pair}>
            <TextField
              label={`Expected salary, lowest (${fixed.currency})`}
              type="number"
              min={1}
              required
              value={draft.expectedMin}
              onChange={set("expectedMin")}
            />
            <TextField
              label={`Expected salary, highest (${fixed.currency})`}
              type="number"
              min={1}
              required
              value={draft.expectedMax}
              onChange={set("expectedMax")}
            />
          </div>
          <TextField
            label="Notice period"
            maxLength={fixed.maxText}
            value={draft.noticePeriod}
            onChange={set("noticePeriod")}
          />
        </Stack>
      </Section>
      <Section title="Daily limit">
        <div className={styles.pair}>
          <TextField
            label="Applications per day"
            hint={`Leave it empty for no limit. LinkedIn stays at ${String(fixed.linkedinCap)} a day whatever you put here.`}
            type="number"
            min={1}
            max={fixed.maxDailyCap}
            value={draft.dailyCap}
            onChange={set("dailyCap")}
          />
        </div>
      </Section>
      {problems.length > 0 && (
        <div className={styles.problems}>
          <Callout tone="bad">
            <p>Nothing was saved. Fix these first:</p>
            <ul>
              {problems.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </Callout>
        </div>
      )}
      <div className={styles.bar}>
        <span className={styles.state} role="status">
          {dirty ? "You have unsaved changes." : "Everything is saved."}
        </span>
        <Row>
          {dirty && (
            <Button
              variant="ghost"
              onClick={() => {
                setEdits(null);
                save.reset();
              }}
            >
              Undo changes
            </Button>
          )}
          <Button type="submit" variant="primary" busy={save.isPending} disabled={!dirty}>
            Save settings
          </Button>
        </Row>
      </div>
    </form>
  );
}

export default function SettingsPage() {
  const { data } = useSuspenseQuery(queries.settings());
  return (
    <div className={styles.page}>
      <PageHeader
        title="Settings"
        description="What to look for and how to answer forms. Changes are used from the next run."
      />
      <SettingsForm view={data} />
    </div>
  );
}
