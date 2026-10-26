import { useSuspenseQuery } from "@tanstack/react-query";
import { type ReactNode, useState } from "react";
import { learnedPaths, useLearnedChange } from "../../api/mutations";
import { queries } from "../../api/queries";
import type { Rule, SavedAnswer, Suggestion } from "../../api/types";
import { RULE_LIMIT, RuleForm } from "../../components/RuleForm";
import { Card, Empty, List, Note, PageHeader, Row, Section, Stack } from "../../ui/Blocks";
import { Button } from "../../ui/Button";
import { TextField } from "../../ui/Fields";
import { toast } from "../../ui/toasts";
import { Editable } from "./Editable";
import styles from "./Learned.module.css";

const ANSWER_LIMIT = 2000;
const SOURCE: Record<SavedAnswer["source"], string> = { user: "From you", ai: "From the AI" };

function Listed({ empty, children }: { empty?: string; children: ReactNode[] }) {
  if (children.length > 0) {
    return <List>{children}</List>;
  }
  return empty ? <Empty>{empty}</Empty> : null;
}

function RuleItem({ rule, label }: { rule: Rule; label: string }) {
  const change = useLearnedChange();
  return (
    <li>
      <Editable
        label={label}
        value={rule.text}
        limit={RULE_LIMIT}
        busy={change.isPending}
        onSave={(text, done) => {
          change.mutate([learnedPaths.editRule(rule.id), { text }], {
            onSuccess: () => {
              done();
              toast("Saved. It's used from the next run.");
            },
          });
        }}
        onDelete={() => {
          change.mutate([learnedPaths.deleteRule(rule.id)], {
            onSuccess: () => {
              toast("Deleted.");
            },
          });
        }}
      />
    </li>
  );
}

function AnswerItem({ answer }: { answer: SavedAnswer }) {
  const change = useLearnedChange();
  const { question } = answer;
  return (
    <li>
      <Editable
        heading={
          <p className={styles.question}>
            {question} <span className={styles.tag}>{SOURCE[answer.source]}</span>
          </p>
        }
        label={question}
        value={answer.answer}
        limit={ANSWER_LIMIT}
        busy={change.isPending}
        onSave={(text, done) => {
          change.mutate([learnedPaths.editAnswer, { question, answer: text }], {
            onSuccess: () => {
              done();
              toast("Answer saved. It's used on the next form that asks.");
            },
          });
        }}
        onDelete={() => {
          change.mutate([learnedPaths.deleteAnswer, { question }], {
            onSuccess: () => {
              toast("Deleted. The next form that asks this waits for you.");
            },
          });
        }}
      />
    </li>
  );
}

function SuggestionItem({ suggestion }: { suggestion: Suggestion }) {
  const change = useLearnedChange();
  const decide = (path: string, message: string) => {
    change.mutate([path], {
      onSuccess: () => {
        toast(message);
      },
    });
  };
  return (
    <li className={styles.item}>
      <p className={styles.text}>Skip jobs with “{suggestion.word}” in the title?</p>
      <Row>
        <Button
          variant="primary"
          busy={change.isPending}
          onClick={() => {
            decide(learnedPaths.accept(suggestion.id), "Added to titles to skip.");
          }}
        >
          Skip them
        </Button>
        <Button
          variant="ghost"
          disabled={change.isPending}
          onClick={() => {
            decide(learnedPaths.dismiss(suggestion.id), "Dismissed.");
          }}
        >
          No thanks
        </Button>
      </Row>
    </li>
  );
}

function SavedAnswers({ answers }: { answers: readonly SavedAnswer[] }) {
  const [query, setQuery] = useState("");
  const words = query.trim().toLowerCase();
  const shown = words
    ? answers.filter((item) => `${item.question} ${item.answer}`.toLowerCase().includes(words))
    : answers;
  return (
    <Section title="Saved answers">
      <Stack>
        <Note>
          Reused when a form asks the same question. Answers you give on a job's page are saved
          here.
        </Note>
        {answers.length > 0 && (
          <TextField label="Find an answer" value={query} onChange={setQuery} />
        )}
        <Listed empty={words ? "No saved answer matches that." : "No saved answers yet."}>
          {shown.map((answer) => (
            <AnswerItem key={answer.question} answer={answer} />
          ))}
        </Listed>
      </Stack>
    </Section>
  );
}

export default function LearnedPage() {
  const { data } = useSuspenseQuery(queries.learned());
  return (
    <div className={styles.page}>
      <PageHeader
        title="What it learned"
        description="Rules, notes and answers SatyaApply uses. Change or delete any of them."
      />
      {data.suggestions.length > 0 && (
        <Section title="Suggestions">
          <Stack>
            <Note>From jobs you dismissed as too senior.</Note>
            <List>
              {data.suggestions.map((suggestion) => (
                <SuggestionItem key={suggestion.id} suggestion={suggestion} />
              ))}
            </List>
          </Stack>
        </Section>
      )}
      <Section title="Your rules">
        <Stack>
          <Listed>
            {data.rules.map((rule) => (
              <RuleItem key={rule.id} rule={rule} label="Edit rule" />
            ))}
          </Listed>
          <Card>
            <RuleForm kind="rule" />
          </Card>
        </Stack>
      </Section>
      <Section title="Tailoring notes">
        <Stack>
          <Listed>
            {data.notes.map((rule) => (
              <RuleItem key={rule.id} rule={rule} label="Edit note" />
            ))}
          </Listed>
          <Card>
            <RuleForm kind="tailoring_note" />
          </Card>
        </Stack>
      </Section>
      <SavedAnswers answers={data.answers} />
    </div>
  );
}
