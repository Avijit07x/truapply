import { useState } from "react";
import { useJobChange } from "../../api/mutations";
import type { JobDetail } from "../../api/types";
import { Note, Row, Section, Stack } from "../../ui/Blocks";
import { Button } from "../../ui/Button";
import { TextField } from "../../ui/Fields";
import { toast } from "../../ui/toasts";

const MAX_ANSWER = 5000;

export function OpenQuestions({ job }: { job: JobDetail }) {
  const change = useJobChange(job.id);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  if (job.questions.length === 0) {
    if (!job.actions.includes("retry")) {
      return null;
    }
    return (
      <Section title="Questions">
        <Stack>
          <Note>Its questions are already answered, maybe on another job.</Note>
          <Row>
            <Button
              variant="primary"
              busy={change.isPending}
              onClick={() => {
                change.mutate(
                  { action: "retry" },
                  {
                    onSuccess: () => {
                      toast("It's filled in again on the next run.");
                    },
                  },
                );
              }}
            >
              Fill it again on the next run
            </Button>
          </Row>
        </Stack>
      </Section>
    );
  }
  const given = Object.entries(answers)
    .filter(([, answer]) => answer.trim())
    .map(([question, answer]) => ({ question, answer }));
  return (
    <Section title="Answer these questions">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          change.mutate(
            { action: "questions", body: { answers: given } },
            {
              onSuccess: () => {
                toast("Saved. It's filled in on the next run, and reused on other forms.");
              },
            },
          );
        }}
      >
        <Stack>
          <Note>
            SatyaApply never guesses legal or eligibility answers. Yours are saved and reused on
            other forms.
          </Note>
          {job.questions.map((item) => (
            <TextField
              key={item.question}
              label={item.label}
              maxLength={MAX_ANSWER}
              value={answers[item.question] ?? ""}
              onChange={(value) => {
                setAnswers((current) => ({ ...current, [item.question]: value }));
              }}
            />
          ))}
          <Row>
            <Button
              type="submit"
              variant="primary"
              busy={change.isPending}
              disabled={given.length === 0}
            >
              Save my answers
            </Button>
          </Row>
        </Stack>
      </form>
    </Section>
  );
}
