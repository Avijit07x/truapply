import { useSuspenseQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { RequestFailed } from "../../api/client";
import { useFinishSetup, useSetupResume } from "../../api/mutations";
import { queries } from "../../api/queries";
import type { Automatic, Extension, SetupAnswers, SetupDraft } from "../../api/types";
import { ExtensionStatus, ExtensionSteps } from "../../components/ExtensionSteps";
import { useExtensionHere } from "../../lib/extension";
import { cx } from "../../lib/cx";
import { RESUME_KINDS, base64 } from "../../lib/files";
import { navigate } from "../../lib/router";
import { Note, PageHeader, Row } from "../../ui/Blocks";
import { Button } from "../../ui/Button";
import { Callout } from "../../ui/Callout";
import { Checkbox, ChoiceField, TagsField, TextField } from "../../ui/Fields";
import { Check } from "../../ui/icons";
import { toast } from "../../ui/toasts";
import { Group } from "../settings/SettingsGroups";
import styles from "./Setup.module.css";

const STEPS = [
  "Your resume",
  "Your details",
  "Rights and pay",
  "How it runs",
  "Extension",
] as const;
const LIST = { maxItems: 50, maxLength: 200 };
const YES_NO = ["Yes", "No"] as const;

type Step = 0 | 1 | 2 | 3 | 4;
type Asking = Exclude<Step, 0>;

const RUNS: Record<string, number | null> = {
  "Only when I press Run": null,
  "Every hour": 60,
  "Every 3 hours": 180,
  "Once a day": 1440,
};
const RESUME = { tailor: "Tailor it to each job", asIs: "Send it as it is" } as const;

function failure(error: unknown): { text: string; problems: readonly string[] } | null {
  return error instanceof RequestFailed ? { text: error.message, problems: error.problems } : null;
}

function Steps({ at }: { at: Step }) {
  return (
    <ol className={styles.steps} aria-label="Setup steps">
      {STEPS.map((label, index) => (
        <li
          key={label}
          className={cx(index < at && styles.done, index === at && styles.now)}
          aria-current={index === at ? "step" : undefined}
        >
          <span className={styles.number}>{index < at ? <Check size={12} /> : index + 1}</span>
          {label}
        </li>
      ))}
    </ol>
  );
}

function ResumeStep() {
  const picker = useRef<HTMLInputElement>(null);
  const read = useSetupResume();
  const failed = failure(read.error);
  const send = async (file: File) => {
    read.mutate({ name: file.name, data: await base64(file) });
  };
  return (
    <Group
      title="Start with your resume"
      note="Claude reads it once to fill in your details and the jobs to look for. Your resume stays on this computer."
    >
      <input
        ref={picker}
        type="file"
        accept={RESUME_KINDS}
        hidden
        aria-label="Resume file"
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          if (file) void send(file);
        }}
      />
      <Row>
        <Button variant="primary" busy={read.isPending} onClick={() => picker.current?.click()}>
          {read.isPending ? "Reading your resume…" : "Choose your resume"}
        </Button>
      </Row>
      <Note>
        {read.isPending
          ? "This takes about a minute. Keep this page open."
          : "PDF, Word, LaTeX, Markdown or plain text, up to 5 MB."}
      </Note>
      {failed && <Callout tone="bad">{failed.text}</Callout>}
    </Group>
  );
}

function startFrom(draft: SetupDraft): SetupAnswers {
  return {
    name: draft.name,
    email: draft.email,
    phone: draft.phone,
    city: draft.city,
    country: draft.country,
    roles: draft.roles,
    titleKeywords: draft.titleKeywords,
    onsiteCity: true,
    remoteCountry: true,
    relocate: false,
    remoteAbroad: false,
    citizenship: "",
    workWithoutVisa: [],
    needsSponsorship: null,
    noticePeriod: "",
    currency: draft.currency,
    expectedMin: null,
    expectedMax: null,
    tailorResume: null,
    jobsPerRun: 5,
    runEveryMinutes: null,
  };
}

type QuestionsProps = {
  draft: SetupDraft;
  noticePeriods: string[];
  automatic: Automatic;
  extension: Extension;
};

type FormProps = {
  answers: SetupAnswers;
  change: (next: Partial<SetupAnswers>) => void;
};

function DetailsStep({ answers, change }: FormProps) {
  const text = (name: "name" | "email" | "phone" | "city" | "country", label: string) => (
    <TextField
      label={label}
      required={name !== "phone"}
      value={answers[name]}
      onChange={(value) => {
        change({ [name]: value });
      }}
    />
  );
  return (
    <>
      <Group title="About you" note="Filled in from your resume. Fix anything that's wrong.">
        <div className={styles.pair}>
          {text("name", "Full name")}
          {text("email", "Email")}
          {text("phone", "Phone")}
          {text("city", "City")}
          {text("country", "Country")}
        </div>
      </Group>
      <Group title="Jobs to look for" note="Suggested from your resume.">
        <TagsField
          label="Job titles you want"
          values={answers.roles}
          onChange={(roles) => {
            change({ roles });
          }}
          {...LIST}
        />
        <TagsField
          label="A job title must contain one of"
          hint="Like frontend or react. Jobs without one of these words are left out."
          values={answers.titleKeywords}
          onChange={(titleKeywords) => {
            change({ titleKeywords });
          }}
          {...LIST}
        />
        <div className={styles.places} role="group" aria-label="Where you'll work">
          <span className={styles.label}>Where you&apos;ll work</span>
          <Checkbox
            label={`On-site or hybrid in ${answers.city || "your city"}`}
            checked={answers.onsiteCity}
            onChange={(onsiteCity) => {
              change({ onsiteCity });
            }}
          />
          <Checkbox
            label={`Remote within ${answers.country || "your country"}`}
            checked={answers.remoteCountry}
            onChange={(remoteCountry) => {
              change({ remoteCountry });
            }}
          />
          <Checkbox
            label="Other cities (you'd move)"
            checked={answers.relocate}
            onChange={(relocate) => {
              change({ relocate });
            }}
          />
          <Checkbox
            label="Remote for companies abroad"
            checked={answers.remoteAbroad}
            onChange={(remoteAbroad) => {
              change({ remoteAbroad });
            }}
          />
        </div>
      </Group>
    </>
  );
}

function amount(value: string): number | null {
  const parsed = Number(value);
  return value.trim() !== "" && Number.isFinite(parsed) ? parsed : null;
}

function RightsStep({ answers, change, noticePeriods }: FormProps & { noticePeriods: string[] }) {
  const sponsorship =
    answers.needsSponsorship === null ? "" : answers.needsSponsorship ? "Yes" : "No";
  return (
    <>
      <Group
        title="Work rights"
        note="Forms ask these. TruApply never guesses them, so only you can fill them in."
      >
        <TextField
          label="Citizenship"
          required
          short
          placeholder="Country"
          value={answers.citizenship}
          onChange={(citizenship) => {
            change({ citizenship });
          }}
        />
        <TagsField
          label="Countries you can work in without a visa"
          values={answers.workWithoutVisa}
          onChange={(workWithoutVisa) => {
            change({ workWithoutVisa });
          }}
          {...LIST}
        />
        <ChoiceField
          label="Would you need visa sponsorship to work in other countries?"
          options={YES_NO}
          value={sponsorship}
          onChange={(picked) => {
            change({ needsSponsorship: picked === "Yes" });
          }}
        />
      </Group>
      <Group title="Notice and pay" note="Used on forms that ask. Yearly amounts.">
        <ChoiceField
          label="Notice period"
          options={noticePeriods}
          value={answers.noticePeriod}
          onChange={(noticePeriod) => {
            change({ noticePeriod });
          }}
        />
        <div className={styles.pay}>
          <TextField
            label="Currency"
            required
            short
            value={answers.currency}
            onChange={(currency) => {
              change({ currency });
            }}
          />
          <TextField
            label="Lowest salary you'd accept"
            type="number"
            min={1}
            required
            value={answers.expectedMin === null ? "" : String(answers.expectedMin)}
            onChange={(value) => {
              change({ expectedMin: amount(value) });
            }}
          />
          <TextField
            label="Highest you'd ask for"
            type="number"
            min={1}
            required
            value={answers.expectedMax === null ? "" : String(answers.expectedMax)}
            onChange={(value) => {
              change({ expectedMax: amount(value) });
            }}
          />
        </div>
      </Group>
    </>
  );
}

function RunsStep({
  answers,
  change,
  runs,
  setRuns,
  automatic,
}: FormProps & { runs: string; setRuns: (runs: string) => void; automatic: Automatic }) {
  const resume =
    answers.tailorResume === null ? "" : answers.tailorResume ? RESUME.tailor : RESUME.asIs;
  return (
    <Group
      title="How it runs"
      note="Each run finds new jobs, scores them and gets the good ones ready. Nothing is ever sent without you."
    >
      {automatic.supported && (
        <ChoiceField
          label="When should it run?"
          options={Object.keys(RUNS)}
          value={runs}
          onChange={(picked) => {
            setRuns(picked);
            change({ runEveryMinutes: RUNS[picked] ?? null });
          }}
        />
      )}
      {automatic.elsewhere && (
        <Note>
          Automatic runs are set up for another TruApply folder on this computer. Picking a time
          here moves them to this one.
        </Note>
      )}
      <ChoiceField
        label="Your resume for each job"
        options={Object.values(RESUME)}
        value={resume}
        onChange={(picked) => {
          change({ tailorResume: picked === RESUME.tailor });
        }}
      />
      <TextField
        label="Jobs to get ready each run"
        hint="1 to 50. Each one uses a few Claude calls."
        type="number"
        min={1}
        max={50}
        required
        value={answers.jobsPerRun === null ? "" : String(answers.jobsPerRun)}
        onChange={(value) => {
          change({ jobsPerRun: amount(value) });
        }}
      />
    </Group>
  );
}

function detailsDone(answers: SetupAnswers): boolean {
  const places =
    answers.onsiteCity || answers.remoteCountry || answers.relocate || answers.remoteAbroad;
  return (
    [answers.name, answers.email, answers.city, answers.country].every((value) => value.trim()) &&
    answers.titleKeywords.length > 0 &&
    places
  );
}

function rightsDone(answers: SetupAnswers): boolean {
  return (
    answers.citizenship.trim() !== "" &&
    answers.workWithoutVisa.length > 0 &&
    answers.needsSponsorship !== null &&
    answers.noticePeriod !== "" &&
    answers.currency.trim() !== "" &&
    answers.expectedMin !== null &&
    answers.expectedMax !== null
  );
}

function runsDone(answers: SetupAnswers, runs: string, automatic: Automatic): boolean {
  return (
    (runs !== "" || !automatic.supported) &&
    answers.tailorResume !== null &&
    answers.jobsPerRun !== null
  );
}

const LEFT: Record<Asking, string> = {
  1: "Add your name, email, city, country, a title word and where you'll work.",
  2: "Answer every question here to go on.",
  3: "Answer every question here to go on.",
  4: "Finish without it if you'll add it later, from Settings.",
};

function ExtensionStep({ extension }: { extension: Extension }) {
  return (
    <Group
      title="Add the Chrome extension"
      note="It fills in applications in your own Chrome, with your own logins. You check each one and press Submit yourself."
    >
      <ExtensionSteps extension={extension} />
      <ExtensionStatus />
    </Group>
  );
}

function Questions({ draft, noticePeriods, automatic, extension }: QuestionsProps) {
  const [step, setStep] = useState<Asking>(1);
  const [runs, setRuns] = useState("");
  const [answers, setAnswers] = useState(() => startFrom(draft));
  const finish = useFinishSetup();
  const here = useExtensionHere();
  const failed = failure(finish.error);
  const change = (next: Partial<SetupAnswers>) => {
    setAnswers((current) => ({ ...current, ...next }));
  };
  const done = {
    1: detailsDone(answers),
    2: rightsDone(answers),
    3: runsDone(answers, runs, automatic),
    4: here,
  }[step];
  const finishSetup = () => {
    finish.mutate(answers, {
      onSuccess: ({ warning }) => {
        toast(warning ?? "You're set up. Press Run now to find your first jobs.");
        navigate("/", true);
      },
    });
  };
  return (
    <>
      <Steps at={step} />
      {step === 1 && <DetailsStep answers={answers} change={change} />}
      {step === 2 && <RightsStep answers={answers} change={change} noticePeriods={noticePeriods} />}
      {step === 3 && (
        <RunsStep
          answers={answers}
          change={change}
          runs={runs}
          setRuns={setRuns}
          automatic={automatic}
        />
      )}
      {step === 4 && <ExtensionStep extension={extension} />}
      {failed && (
        <Callout tone="bad">
          {failed.text}
          {failed.problems.length > 0 && (
            <ul>
              {failed.problems.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          )}
        </Callout>
      )}
      <div className={styles.actions}>
        {step > 1 && (
          <Button
            onClick={() => {
              setStep((step - 1) as Asking);
            }}
          >
            Back
          </Button>
        )}
        <Note>{done ? "" : LEFT[step]}</Note>
        {step === 4 && !here && (
          <Button busy={finish.isPending} onClick={finishSetup}>
            Finish without it
          </Button>
        )}
        <Button
          variant="primary"
          disabled={!done}
          busy={finish.isPending}
          onClick={() => {
            if (step === 4) {
              finishSetup();
              return;
            }
            setStep((step + 1) as Asking);
          }}
        >
          {step === 4 ? "Finish setup" : "Next"}
        </Button>
      </div>
    </>
  );
}

export default function SetupPage() {
  const { data } = useSuspenseQuery(queries.setup());
  return (
    <>
      <PageHeader
        title="Set up TruApply"
        description="Five short steps. You can change anything later in Settings."
      />
      <div className={styles.page}>
        {data.draft ? (
          <Questions
            draft={data.draft}
            noticePeriods={data.noticePeriods}
            automatic={data.automatic}
            extension={data.extension}
          />
        ) : (
          <>
            <Steps at={0} />
            <ResumeStep />
          </>
        )}
      </div>
    </>
  );
}
