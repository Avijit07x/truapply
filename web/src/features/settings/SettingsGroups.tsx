import type { ReactNode } from "react";
import type { SettingsLimits, SettingsValues } from "../../api/types";
import { Checkbox, SelectField, TagsField, TextField } from "../../ui/Fields";
import { type Clock, useClock } from "../../lib/clock";
import type { Draft, NumberName } from "./draft";
import { INFO, REMOTE_ABROAD_INFO, UNKNOWN_INFO } from "./info";
import styles from "./Settings.module.css";

type Set = <Name extends keyof Draft>(name: Name) => (value: Draft[Name]) => void;
export type GroupProps = { draft: Draft; set: Set; limits: SettingsLimits };
type NamesOf<Kind> = {
  [Name in keyof Draft]: Draft[Name] extends Kind ? Name : never;
}[keyof Draft];

const UNKNOWN: Record<SettingsValues["unknownQuestions"], string> = {
  skip: "Leave them for me to answer",
  guess: "Give the most sensible answer from my facts",
};
const COMPANY_SEARCH: Record<SettingsValues["companySearch"], string> = {
  weekly: "Every week",
  daily: "Every day",
  off: "Never",
};
const RESUME = {
  tailor: "Tailor it to each job",
  original: "Always send my resume as it is",
} as const;
const SHORT_ANSWERS: ReadonlySet<string> = new Set(["citizenship", "currency", "noticePeriod"]);
const COVER: Record<SettingsValues["coverLetter"], string> = {
  required: "Only when the form needs one",
  always: "Whenever there's a cover letter box",
  never: "Never",
};

export function Group({
  title,
  note,
  children,
}: {
  title: string;
  note: string;
  children: ReactNode;
}) {
  return (
    <section className={styles.group}>
      <div className={styles.groupHead}>
        <h2 className={styles.groupTitle}>{title}</h2>
        <p className={styles.groupNote}>{note}</p>
      </div>
      <div className={styles.fields}>{children}</div>
    </section>
  );
}

export function fieldsFor({ draft, set, limits }: GroupProps) {
  const list = { maxItems: limits.maxItems, maxLength: limits.maxText };
  const text = (name: NamesOf<string>, label: string, hint?: string, required = false) => (
    <TextField
      label={label}
      hint={hint}
      info={INFO[name]}
      maxLength={limits.maxText}
      required={required}
      short={SHORT_ANSWERS.has(name)}
      value={draft[name]}
      onChange={set(name)}
    />
  );
  const tags = (name: NamesOf<string[]>, label: string, hint?: string) => (
    <TagsField
      label={label}
      hint={hint}
      info={INFO[name]}
      values={draft[name]}
      onChange={set(name)}
      {...list}
    />
  );
  const number = (name: NumberName, label: string, hint?: string, required = true) => {
    const range = limits.numbers[name] ?? { min: 0, max: Number.MAX_SAFE_INTEGER };
    return (
      <TextField
        label={label}
        hint={
          hint === ""
            ? undefined
            : (hint ?? `${range.min.toLocaleString()} to ${range.max.toLocaleString()}.`)
        }
        info={INFO[name]}
        type="number"
        min={range.min}
        max={range.max}
        step={name === "yearsExperience" ? "any" : 1}
        required={required}
        value={draft[name]}
        onChange={set(name)}
      />
    );
  };
  const choice = <Key extends string>(
    label: string,
    names: Record<Key, string>,
    value: Key,
    onChange: (value: Key) => void,
    info?: string,
  ) => (
    <SelectField
      label={label}
      info={info}
      value={names[value]}
      options={Object.values(names)}
      onChange={(picked) => {
        const found = (Object.keys(names) as Key[]).find((key) => names[key] === picked);
        if (found) onChange(found);
      }}
    />
  );
  return { text, tags, number, choice };
}

export function AboutYou(props: GroupProps) {
  const { text, tags, number } = fieldsFor(props);
  return (
    <Group title="About you" note="Used on your resume and to fill in every application form.">
      <div className={styles.pair}>
        {text("name", "Full name", undefined, true)}
        {text("email", "Email", undefined, true)}
      </div>
      <div className={styles.pair}>
        {text("phone", "Phone")}
        {text("currentCompany", "Current company")}
      </div>
      <div className={styles.pair}>
        {text("city", "City", undefined, true)}
        {text("country", "Country", undefined, true)}
      </div>
      {tags("links", "Links", "LinkedIn, GitHub, portfolio.")}
      <div className={styles.pair}>
        {number("yearsExperience", "Years of experience", "Like 2.5.")}
      </div>
    </Group>
  );
}

export function JobSearch(props: GroupProps) {
  const { tags, number, choice } = fieldsFor(props);
  const { draft, set } = props;
  return (
    <Group
      title="Job search"
      note="Which jobs to look for. Jobs scoring below the minimum match score are skipped."
    >
      {tags("roles", "Roles you want", "Used to search the web for new jobs.")}
      {tags("titleKeywords", "Title keywords")}
      {tags("titleExclude", "Titles to skip")}
      {tags("skipCompanies", "Companies to skip")}
      <div className={styles.pair}>
        {number("maxJobAgeDays", "Oldest job to consider, in days")}
        {number("minScore", "Minimum match score")}
      </div>
      {choice(
        "Search the web for new companies",
        COMPANY_SEARCH,
        draft.companySearch,
        set("companySearch"),
      )}
    </Group>
  );
}

export function Wellfound(props: GroupProps) {
  const { tags } = fieldsFor(props);
  const { draft, set } = props;
  return (
    <Group
      title="Wellfound"
      note="Wellfound jobs get their own tab. They aren't scored and your resume isn't tailored for them; you apply on Wellfound yourself. Jobs that need more experience than you have, or skills you don't list, are left out."
    >
      <Checkbox
        label="List Wellfound jobs on every run"
        checked={draft.wellfound}
        onChange={set("wellfound")}
      />
      {draft.wellfound && (
        <>
          {tags(
            "wellfoundRoles",
            "Wellfound roles to read",
            "Wellfound's own role pages, like Frontend Engineer or Full Stack Engineer. Empty uses Roles you want.",
          )}
          {tags(
            "wellfoundTitles",
            "Pull jobs whose title has",
            "Like frontend, full stack or MERN. Empty uses your roles and title keywords.",
          )}
          {tags(
            "wellfoundSkip",
            "Skip jobs whose title has",
            "Like java, php or python. Titles to skip above always apply too.",
          )}
        </>
      )}
    </Group>
  );
}

export function WorkPlaces({ draft, set, limits }: GroupProps) {
  const { tags } = fieldsFor({ draft, set, limits });
  const city = draft.city || "your city";
  const country = draft.country || "your country";
  return (
    <Group
      title="Where you'll work"
      note="Tick every kind of place you're happy to work. Jobs anywhere else are skipped."
    >
      <Checkbox
        label={`On-site or hybrid in ${city}`}
        checked={draft.onsiteCity}
        onChange={set("onsiteCity")}
      />
      <Checkbox
        label={`Remote in ${country}`}
        checked={draft.remoteCountry}
        onChange={set("remoteCountry")}
      />
      <Checkbox
        label={`Moving to another city in ${country}`}
        checked={draft.relocate}
        onChange={set("relocate")}
      />
      {draft.relocate && tags("relocateCities", "Cities you'd move to")}
      <Checkbox
        label="Remote for companies abroad"
        info={REMOTE_ABROAD_INFO}
        checked={draft.remoteAbroad}
        onChange={set("remoteAbroad")}
      />
    </Group>
  );
}

export function PayAndNotice(props: GroupProps) {
  const { text, number } = fieldsFor(props);
  const currency = props.draft.currency || "currency";
  return (
    <Group title="Pay and notice" note="Used to answer pay and notice questions on forms.">
      <div className={styles.pair}>
        {text("currency", "Currency", "Like INR or USD.", true)}
        {number(
          "currentSalary",
          `Current salary (${currency})`,
          "Leave it empty to not share it.",
          false,
        )}
      </div>
      <div className={styles.pair}>
        {number("expectedMin", `Expected salary, lowest (${currency})`, "")}
        {number("expectedMax", `Expected salary, highest (${currency})`, "")}
      </div>
      {text("noticePeriod", "Notice period")}
    </Group>
  );
}

export function WorkRights(props: GroupProps) {
  const { text, tags } = fieldsFor(props);
  const { draft, set } = props;
  return (
    <Group
      title="Work rights"
      note="Legal questions are only ever answered from these. Nothing here is guessed."
    >
      {text("citizenship", "Citizenship")}
      {tags("workWithoutVisa", "Countries you can work in without a visa")}
      <Checkbox
        label="I need visa sponsorship to work anywhere else"
        checked={draft.needsSponsorship}
        onChange={set("needsSponsorship")}
      />
    </Group>
  );
}

export function PersonalDetails(props: GroupProps) {
  const { text } = fieldsFor(props);
  const { draft, set } = props;
  const blank = "Leave it empty to answer “Prefer not to say”.";
  return (
    <Group
      title="Personal details"
      note="Only for forms that ask. Leave any of these empty and it won't be shared."
    >
      <div className={styles.pair}>
        <TextField
          label="Date of birth"
          hint="Leave it empty to not share it."
          type="date"
          value={draft.dateOfBirth}
          onChange={set("dateOfBirth")}
        />
        {text("gender", "Gender", blank)}
      </div>
      <div className={styles.pair}>
        {text("disability", "Disability", blank)}
        {text("veteran", "Veteran status", blank)}
      </div>
      {text("ethnicity", "Ethnicity", blank)}
    </Group>
  );
}

export function MoreFacts({ draft, set, limits }: GroupProps) {
  return (
    <Group
      title="Other true facts"
      note="Anything true that isn't on your resume. Claude may use it on forms, never more."
    >
      <TextField
        label="Facts about you"
        hint={`Up to ${limits.maxLongText.toLocaleString()} characters.`}
        multiline
        rows={5}
        maxLength={limits.maxLongText}
        value={draft.extraFacts}
        onChange={set("extraFacts")}
      />
    </Group>
  );
}

export function FormAnswers(props: GroupProps) {
  const { choice } = fieldsFor(props);
  const { draft, set } = props;
  return (
    <Group
      title="Form answers"
      note="What to do with questions your facts don't answer. Legal and consent ones are always left for you."
    >
      {choice(
        "Questions it can't answer",
        UNKNOWN,
        draft.unknownQuestions,
        set("unknownQuestions"),
        UNKNOWN_INFO,
      )}
      {choice("Write a cover letter", COVER, draft.coverLetter, set("coverLetter"))}
    </Group>
  );
}

export function ResumeChoice(props: GroupProps) {
  const { choice } = fieldsFor(props);
  const { draft, set } = props;
  return (
    <Group
      title="Your resume"
      note="Tailoring rewrites your resume for each good match with Claude, using only facts from your resume and notes. If you'd rather send the same resume everywhere, choose to send it as it is. That also uses fewer Claude calls."
    >
      {choice("For each job", RESUME, draft.tailorResume ? "tailor" : "original", (picked) => {
        set("tailorResume")(picked === "tailor");
      })}
    </Group>
  );
}

export function AutoSubmit(props: GroupProps) {
  const { number } = fieldsFor(props);
  const { draft, set } = props;
  return (
    <Group
      title="Auto-submit"
      note="The extension sends a job in your Chrome by itself after a run, but only when no consent box, required question or human check is left for you. Optional questions it can't answer stay blank. Otherwise it stops before Submit and leaves the tab for you. Only jobs made ready after you turn it on are sent. Two 👎 on the last 10 it sent turn it off."
    >
      <Checkbox
        label="Send strong matches by itself"
        checked={draft.autoSubmit}
        onChange={set("autoSubmit")}
      />
      {draft.autoSubmit && (
        <div className={styles.pair}>{number("autoSubmitScore", "Send from score")}</div>
      )}
    </Group>
  );
}

export function RunsAndLimits(props: GroupProps) {
  const { number } = fieldsFor(props);
  return (
    <Group title="Runs and limits" note="How much each run does, and the most for one day.">
      <div className={styles.pair}>
        {number(
          "jobsPerRun",
          "Jobs to get ready each run",
          "Also the starting number on the Run page.",
        )}
        {number("scoresPerRun", "Jobs to score each run")}
      </div>
      <div className={styles.pair}>
        {number("dailyCap", "Applications per day", "Leave it empty for no limit.", false)}
        {number("linkedinCap", "LinkedIn applications per day")}
      </div>
      <div className={styles.pair}>{number("aiCallsPerDay", "Claude calls per day")}</div>
    </Group>
  );
}

const CLOCKS: Record<Clock, string> = {
  system: "Same as my Mac",
  "12": "12-hour (5:18 pm)",
  "24": "24-hour (17:18)",
};

export function TimeFormat() {
  const { clock, setClock } = useClock();
  return (
    <Group title="Time format" note="How times show across the app. Changes right away.">
      <SelectField
        label="Clock"
        value={CLOCKS[clock]}
        options={Object.values(CLOCKS)}
        onChange={(picked) => {
          const found = (Object.keys(CLOCKS) as Clock[]).find((key) => CLOCKS[key] === picked);
          if (found) setClock(found);
        }}
      />
    </Group>
  );
}
