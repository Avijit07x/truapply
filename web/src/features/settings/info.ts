import type { Draft } from "./draft";

export const INFO: Partial<Record<keyof Draft, string>> = {
  yearsExperience:
    "Used to answer “years of experience” questions on forms, and given to Claude with your resume. Wellfound jobs that ask for more than a year beyond this are left out.",
  roles:
    "Used to search the web for new companies and for Wellfound. It doesn't decide which jobs are kept: Title keywords does that.",
  titleKeywords:
    "A job is kept only if its title has one of these. A plain title like “Software Engineer” is also kept when its description mentions your stack.",
  titleExclude:
    "A job whose title has any of these is skipped, even when it matches a keyword. Use it for levels you don't want, like staff, lead or principal.",
  skipCompanies: "Jobs from these companies are never scored or applied to.",
  maxJobAgeDays:
    "Jobs posted longer ago than this are skipped. Many companies keep a job listed for months while it's still open, so a higher number finds more jobs. Jobs with no posting date are always kept.",
  minScore:
    "Claude scores each job from 0 to 100 against your resume and rules. Jobs below this are skipped, so your resume isn't tailored for them. Lower it to see more jobs; raise it to see fewer, closer matches.",
  relocateCities:
    "Jobs in these cities are kept as well as your own. Leave it empty to keep jobs in any city in your country.",
  noticePeriod: "Used word for word to answer notice-period questions on forms.",
  workWithoutVisa:
    "Work-authorization questions are answered only from this and the sponsorship box below. Nothing about your right to work is ever guessed.",
  extraFacts:
    "True things about you that aren't on your resume, like older projects, certifications or languages you speak. Tailoring and form answers may use these as well as your resume, and nothing else.",
  autoSubmitScore:
    "Only jobs that score at least this are sent by themselves. The rest wait for you.",
  jobsPerRun:
    "How many resumes each run tailors. Each one takes a few Claude calls, and each becomes a job ready for you to apply.",
  scoresPerRun:
    "How many new jobs each run sends to Claude to score. Jobs left over are scored on the next run.",
  dailyCap:
    "The most resumes TruApply gets ready in one day, across all runs. Leave it empty for no limit.",
  linkedinCap: "The most LinkedIn jobs TruApply gets ready in one day.",
  aiCallsPerDay:
    "Every Claude call counts toward this. When it's used up, TruApply stops calling Claude until tomorrow, so a busy day can't use up your Claude plan.",
  runEveryMinutes:
    "Automatic runs start at set times counted from midnight. Every 180 minutes means 00:00, 03:00, 06:00 and so on. A run missed while the computer sleeps starts when it wakes.",
  summaryHour:
    "The daily summary is written after the first run past this hour, as a notification and a summary file.",
};

export const UNKNOWN_INFO =
  "“Leave them for me to answer” leaves any question your facts don't answer empty, for you to fill in. “Give the most sensible answer” lets Claude answer it from your facts, and marks the answer as a guess. Legal and consent questions are always left for you.";
export const REMOTE_ABROAD_INFO =
  "Keeps remote jobs anyone anywhere can take, like “Remote” or “Worldwide”. Remote jobs tied to another country, like “Remote, US”, are still skipped.";
