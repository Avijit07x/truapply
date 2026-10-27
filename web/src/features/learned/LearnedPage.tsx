import { Tabs } from "@base-ui/react/tabs";
import { useSuspenseQuery } from "@tanstack/react-query";
import { useState } from "react";
import { learnedPaths, useLearnedChange } from "../../api/mutations";
import { queries } from "../../api/queries";
import type { Rule, RuleKind, SavedAnswer, Suggestion } from "../../api/types";
import { RULE_LIMIT, RuleForm } from "../../components/RuleForm";
import { plural } from "../../lib/format";
import { PageHeader, Row } from "../../ui/Blocks";
import { Button } from "../../ui/Button";
import { SearchBox } from "../../ui/SearchBox";
import { type TabItem, TabList } from "../../ui/Tabs";
import { toast } from "../../ui/toasts";
import { Editable } from "./Editable";
import { grouped } from "./groups";
import styles from "./Learned.module.css";

const ANSWER_LIMIT = 2000;

function RuleItem({ rule, kind }: { rule: Rule; kind: RuleKind }) {
  const change = useLearnedChange();
  const name = kind === "rule" ? "rule" : "note";
  return (
    <li>
      <Editable
        label={kind === "rule" ? "Rule" : "Tailoring note"}
        name={`${name}: ${rule.text}`}
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

function AnswerItem({ answer, compact }: { answer: SavedAnswer; compact: boolean }) {
  const change = useLearnedChange();
  const { question } = answer;
  return (
    <li>
      <Editable
        compact={compact}
        heading={
          <>
            <span className={compact ? styles.label : styles.question}>{question}</span>
            {!compact && answer.source === "ai" && (
              <span className={styles.ai} title="Written by the AI from your resume and notes">
                AI
              </span>
            )}
          </>
        }
        label={question}
        name={`answer to ${question}`}
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
    <>
      <div className={styles.toolbar}>
        <SearchBox
          label="Find a saved answer"
          placeholder="Find a question or answer"
          value={query}
          onSearch={setQuery}
        />
        <p className={styles.hint}>
          Reused when a form asks the same question. Written answers marked AI were drafted from
          your resume and notes, so they're worth a quick read.
        </p>
      </div>
      {shown.length > 0 ? (
        grouped(shown).map((group) => (
          <section key={group.title} className={styles.group} aria-label={group.title}>
            <h3 className={styles.groupTitle}>
              {group.title}
              <span className={styles.groupCount}>{group.answers.length}</span>
            </h3>
            <ul className={styles.list}>
              {group.answers.map((answer) => (
                <AnswerItem key={answer.question} answer={answer} compact={!group.written} />
              ))}
            </ul>
          </section>
        ))
      ) : (
        <p className={styles.empty}>
          {words ? "No saved answer matches that." : "No saved answers yet."}
        </p>
      )}
    </>
  );
}

function RulesPanel({
  kind,
  items,
  empty,
}: {
  kind: RuleKind;
  items: readonly Rule[];
  empty: string;
}) {
  return (
    <>
      <div className={styles.add}>
        <RuleForm kind={kind} />
      </div>
      {items.length > 0 ? (
        <ul className={styles.list}>
          {items.map((rule) => (
            <RuleItem key={rule.id} rule={rule} kind={kind} />
          ))}
        </ul>
      ) : (
        <p className={styles.empty}>{empty}</p>
      )}
    </>
  );
}

export default function LearnedPage() {
  const { data } = useSuspenseQuery(queries.learned());
  const tabs: TabItem[] = [
    ...(data.suggestions.length > 0
      ? [{ value: "suggestions", label: "Suggestions", count: data.suggestions.length }]
      : []),
    { value: "rules", label: "Your rules", count: data.rules.length },
    { value: "notes", label: "Tailoring notes", count: data.notes.length },
    { value: "answers", label: "Saved answers", count: data.answers.length },
  ];
  return (
    <div className={styles.page}>
      <PageHeader
        title="What it learned"
        description={`${plural(data.rules.length, "rule")}, ${plural(data.notes.length, "tailoring note")} and ${plural(data.answers.length, "saved answer")}. Change or delete any of them.`}
      />
      <Tabs.Root defaultValue={tabs[0]?.value ?? "rules"} className={styles.tabs}>
        <TabList label="What it learned" items={tabs} />
        <Tabs.Panel value="suggestions" className={styles.panel}>
          <p className={styles.hint}>From jobs you dismissed as too senior.</p>
          <ul className={styles.list}>
            {data.suggestions.map((suggestion) => (
              <SuggestionItem key={suggestion.id} suggestion={suggestion} />
            ))}
          </ul>
        </Tabs.Panel>
        <Tabs.Panel value="rules" className={styles.panel}>
          <RulesPanel
            kind="rule"
            items={data.rules}
            empty="No rules yet. Rules change how jobs are scored."
          />
        </Tabs.Panel>
        <Tabs.Panel value="notes" className={styles.panel}>
          <RulesPanel
            kind="tailoring_note"
            items={data.notes}
            empty="No tailoring notes yet. Notes change how your resume is tailored."
          />
        </Tabs.Panel>
        <Tabs.Panel value="answers" className={styles.panel}>
          <SavedAnswers answers={data.answers} />
        </Tabs.Panel>
      </Tabs.Root>
    </div>
  );
}
