import { useState } from "react";
import { useJobChange } from "../../api/mutations";
import type { JobDetail, Sent } from "../../api/types";
import { Empty, Note, Row, Section, Stack } from "../../ui/Blocks";
import { Button } from "../../ui/Button";
import { TextField } from "../../ui/Fields";
import { toast } from "../../ui/toasts";
import styles from "./Job.module.css";

const MAX_ANSWER = 5000;

function AnswerList({ sent }: { sent: readonly Sent[] }) {
  return (
    <dl className={styles.answers}>
      {sent.map((item, index) => (
        <div key={`${String(index)}-${item.question}`} className={styles.answer}>
          <dt>{item.question}</dt>
          <dd>{item.answer}</dd>
        </div>
      ))}
    </dl>
  );
}

function AnswerEditor({ job }: { job: JobDetail }) {
  const change = useJobChange(job.id);
  const [drafts, setDrafts] = useState(() => job.sent.map((item) => item.answer));
  const changed = job.sent.flatMap((item, index) => {
    const draft = drafts[index]?.trim() ?? "";
    return item.editable && draft && draft !== item.answer
      ? [{ question: item.question, answer: draft }]
      : [];
  });
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        change.mutate(
          { action: "answers", body: { answers: changed } },
          {
            onSuccess: () => {
              toast("Answers saved. They're also saved for future forms.");
            },
          },
        );
      }}
    >
      <Stack>
        <Note>
          Change any answer before you approve. Changed answers are reused on future forms.
        </Note>
        {job.sent.map((item, index) =>
          item.editable ? (
            <TextField
              key={`${String(index)}-${item.question}`}
              label={item.question}
              multiline
              rows={2}
              maxLength={MAX_ANSWER}
              value={drafts[index] ?? ""}
              onChange={(value) => {
                setDrafts((current) => current.map((text, at) => (at === index ? value : text)));
              }}
            />
          ) : (
            <AnswerList key={`${String(index)}-${item.question}`} sent={[item]} />
          ),
        )}
        <Row>
          <Button type="submit" busy={change.isPending} disabled={changed.length === 0}>
            Save changes
          </Button>
        </Row>
      </Stack>
    </form>
  );
}

export function FilledAnswers({ job }: { job: JobDetail }) {
  if (job.sent.length === 0) {
    return (
      <Section title="What was filled in">
        <Empty>Nothing filled in yet.</Empty>
      </Section>
    );
  }
  return (
    <Section title="What was filled in">
      {job.actions.includes("answers") ? (
        <AnswerEditor job={job} />
      ) : (
        <AnswerList sent={job.sent} />
      )}
    </Section>
  );
}
