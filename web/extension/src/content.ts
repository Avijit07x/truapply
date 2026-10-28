import { FIELD_ATTR, controlsOf, readFields } from "./fields";
import { fillField, readChoices, recommit, sleep } from "./fill";
import { failed } from "./messages";
import type {
  Added,
  Answers,
  Field,
  Go,
  Job,
  Reply,
  Request,
  Resume,
  Sending,
  SentItem,
} from "./messages";
import { readPage } from "./posting";
import { openPanel, stayOnPage } from "./panel";
import type { Panel } from "./panel";

const CONFIRMED =
  /application (was |has been )?(successfully )?(submitted|sent|received)|thank(s| you) for (applying|your application|submitting)|successfully (applied|submitted)|we('ve| have) received your application|you('ve| have) (successfully )?applied/i;
const FORM_WAIT_MS = 20_000;
const POLL_MS = 300;
const BUSY = "data-truapply-busy";
const SAVE_START_MS = 60;
const SAVE_WAIT_MS = 4000;
const QUIET_MS = 120;
const STEP_MS = 40;
const UPLOAD_WAIT_MS = 10_000;
const UPLOAD_SETTLE_MS = 1500;
const STEADY_READS = 2;
const SETTLE_MS = 800;
const WATCH_MS = 1500;
const MOST_FIELDS_LEFT = 2;
const OUTLINE = "3px solid #f5b800";
const REQUIRED_WHY = "required; fill it yourself";
const NO_SUGGESTION_WHY = "none of its suggestions matched your answer";
const NOTE_KEY = "";
const MAX_ROUNDS = 4;
const MAX_ATTEMPTS = 2;
const CONFIRM_WAIT_MS = 45_000;
const NAMED_LEFT = 3;
const CHECK_FRAME =
  /recaptcha|hcaptcha|challenges\.cloudflare\.com|turnstile|arkoselabs|funcaptcha/i;
const SUBMIT_TEXT = /^(submit( (my |your )?application)?|apply( now)?|send( my)? application)$/i;
const SAYS_SUBMIT = /submit|send/i;
const SHOWN = { opacityProperty: true, visibilityProperty: true };

type State =
  | "loading"
  | "unknown"
  | "offline"
  | "adding"
  | "shown"
  | "filling"
  | "filled"
  | "broken"
  | "applied";

let shown: { state: State; report: string } = { state: "loading", report: "" };
const clicked = (globalThis as { truapplyClicked?: boolean }).truapplyClicked === true;

const restore = () => {
  const root = document.documentElement.dataset;
  if (root.truapply !== shown.state) root.truapply = shown.state;
  if (shown.report && root.truapplyReport !== shown.report) root.truapplyReport = shown.report;
};

const mark = (state: State, report?: object) => {
  shown = { state, report: report ? JSON.stringify(report) : shown.report };
  restore();
};

const ask = <T>(request: Request): Promise<Reply<T>> =>
  chrome.runtime.sendMessage<Reply<T>>(request).catch(() => ({ error: "offline" }));

const touched = new Set<string>();
const filled = new Map<string, string>();
const answered = new Map<string, string>();
const reasons = new Map<string, string>();
const attempts = new Map<string, number>();
const consents = new Set<string>();
const keyOf = (field: Field) => `${field.kind}:${field.label}`;
const plural = (count: number) => (count === 1 ? "1 answer" : `${String(count)} answers`);
let quickDone = false;
const timings: { step: string; ms: number }[] = [];

async function timed<T>(step: string, work: Promise<T>): Promise<T> {
  const started = performance.now();
  const result = await work;
  timings.push({ step, ms: Math.round(performance.now() - started) });
  return result;
}

function noteTouch(event: Event): void {
  const target = event.target instanceof Element ? event.target : null;
  const id = target?.closest(`[${FIELD_ATTR}]`)?.getAttribute(FIELD_ATTR);
  if (event.isTrusted && id) touched.add(id);
}

const since = (start: number) => performance.now() - start;

async function waitForForm(): Promise<Field[]> {
  let seen = -1;
  let steady = 0;
  for (const start = performance.now(); since(start) < FORM_WAIT_MS;) {
    const fields = readFields();
    steady = fields.length && fields.length === seen ? steady + 1 : 0;
    if (steady >= STEADY_READS) return fields;
    seen = fields.length;
    await sleep(POLL_MS);
  }
  return readFields();
}

async function withChoices(fields: Field[]): Promise<Field[]> {
  const ready: Field[] = [];
  for (const field of fields) {
    const open = field.kind === "combobox" && !field.options.length && !field.value;
    ready.push(open ? { ...field, options: await readChoices(field) } : field);
  }
  return ready;
}

function resumeLoader(job: Job): () => Promise<File | null> {
  let loading: Promise<File | null> | null = null;
  const load = async () => {
    const reply = await ask<Resume>({ type: "resume", jobId: job.id });
    if (failed(reply) || !job.resume) return null;
    const bytes = Uint8Array.from(atob(reply.data), (char) => char.charCodeAt(0));
    return new File([bytes], job.resume, { type: "application/pdf" });
  };
  return () => (loading ??= load());
}

const needsWork = (field: Field) =>
  !field.value &&
  !reasons.has(keyOf(field)) &&
  (!answered.has(keyOf(field)) || (attempts.get(keyOf(field)) ?? 0) < MAX_ATTEMPTS);

async function askFor(job: Job, fields: Field[], ai: boolean): Promise<string | null> {
  const fresh = fields.filter((field) => !answered.has(keyOf(field)));
  if (!fresh.length) return null;
  const withOptions = await timed("read choices", withChoices(fresh));
  const reply = await timed(
    `answers for ${String(fresh.length)}`,
    ask<Answers>({ type: "answers", jobId: job.id, fields: withOptions, ai }),
  );
  if (failed(reply)) return reply.error;
  const byId = new Map(fresh.map((field) => [field.id, field]));
  const waiting = new Set(reply.waiting);
  for (const field of fresh) if (!waiting.has(field.id)) answered.set(keyOf(field), "");
  for (const { id, value } of reply.answers) {
    const field = byId.get(id);
    if (field) answered.set(keyOf(field), value);
  }
  for (const { id, why, consent } of reply.forYou) {
    const field = byId.get(id);
    if (field) reasons.set(keyOf(field), why);
    if (field && consent) consents.add(keyOf(field));
  }
  if (reply.note) reasons.set(NOTE_KEY, reply.note);
  return null;
}

const pageRequests = () => Number(document.documentElement.getAttribute(BUSY) ?? 0);

async function pageSettled(): Promise<void> {
  await sleep(SAVE_START_MS);
  let quietFrom = performance.now();
  for (const start = performance.now(); since(start) < SAVE_WAIT_MS;) {
    if (pageRequests()) quietFrom = performance.now();
    else if (since(quietFrom) >= QUIET_MS) return;
    await sleep(STEP_MS);
  }
}

const filesFirst = (a: Field, b: Field) => Number(b.kind === "file") - Number(a.kind === "file");

async function uploaded(name: string): Promise<void> {
  for (const start = performance.now(); since(start) < UPLOAD_WAIT_MS;) {
    if (document.body.innerText.includes(name)) break;
    await sleep(POLL_MS);
  }
  await sleep(UPLOAD_SETTLE_MS);
}

async function fillRound(
  job: Job,
  fields: Field[],
  resume: () => Promise<File | null>,
  panel: Panel,
) {
  const open = fields.filter(needsWork);
  const ai = quickDone;
  quickDone = true;
  const fresh = open.filter((field) => !answered.has(keyOf(field))).length;
  if (ai && fresh) panel.wait(`Profile answers are in. Claude is answering ${plural(fresh)} …`);
  const problem = await askFor(job, open, ai);
  if (problem) return problem;
  for (const field of [...open].sort(filesFirst)) {
    const value = answered.get(keyOf(field));
    if (!value) continue;
    attempts.set(keyOf(field), (attempts.get(keyOf(field)) ?? 0) + 1);
    if (await timed(`fill ${field.kind}`, fillField(field, value, resume))) {
      filled.set(field.id, value);
      await pageSettled();
      if (field.kind === "file" && job.resume) {
        panel.wait("Attaching your resume …");
        await timed("upload", uploaded(job.resume));
        panel.wait("Filling the form …");
      }
    } else if (field.kind === "combobox" && !field.options.length) {
      reasons.set(keyOf(field), NO_SUGGESTION_WHY);
    }
  }
  return null;
}

function leftForYou(fields: Field[]) {
  return fields
    .filter((field) => reasons.has(keyOf(field)) || (field.required && !field.value))
    .map((field) => ({ field, why: reasons.get(keyOf(field)) ?? REQUIRED_WHY }));
}

function snapshot(): SentItem[] {
  return readFields()
    .filter((field) => field.value && field.kind !== "file")
    .map((field) => ({
      question: field.label,
      answer: field.value,
      kind: field.kind,
      yours: touched.has(field.id) || !filled.has(field.id),
    }));
}

const isThankYou = () =>
  CONFIRMED.test(document.body.innerText) && readFields().length <= MOST_FIELDS_LEFT;

const sentKey = (job: Job) => `sent:${String(job.id)}`;

async function savedAnswers(job: Job): Promise<SentItem[]> {
  const stored = await chrome.storage.local.get(sentKey(job));
  const items = stored[sentKey(job)];
  return Array.isArray(items) ? (items as SentItem[]) : [];
}

async function markApplied(job: Job, panel: Panel, sent: SentItem[]): Promise<void> {
  const reply = await ask<object>({ type: "applied", jobId: job.id, sent });
  if (failed(reply)) {
    panel.say(`Sent, but TruApply didn't save it: ${reply.error}`);
    return;
  }
  void chrome.storage.local.remove(sentKey(job));
  mark("applied");
  panel.say("Sent. Saved as applied in TruApply.");
  panel.list([]);
}

function watch(job: Job, panel: Panel): void {
  let last = snapshot();
  const keep = (event: Event) => {
    if (!event.isTrusted) return;
    last = snapshot();
    void chrome.storage.local.set({ [sentKey(job)]: last });
  };
  document.addEventListener("change", keep, true);
  document.addEventListener("submit", keep, true);
  document.addEventListener("pointerdown", keep, true);
  const timer = setInterval(() => {
    if (!isThankYou()) return;
    clearInterval(timer);
    void markApplied(job, panel, last);
  }, WATCH_MS);
}

function finish(fields: Field[], panel: Panel): string[] {
  const left = leftForYou(fields);
  for (const { field } of left) {
    for (const element of controlsOf(field.id)) element.style.outline = OUTLINE;
  }
  panel.say(
    left.length === 1
      ? "Filled. 1 thing is yours, then press Submit:"
      : left.length
        ? `Filled. ${String(left.length)} things are yours, then press Submit:`
        : "Filled. Check it, then press Submit.",
  );
  panel.list(left.map(({ field, why }) => ({ label: field.label, why })));
  mark("filled", {
    fields: fields.map(({ label, kind, required, value }) => ({
      label,
      kind,
      required,
      filled: !!value,
    })),
    forYou: left.filter(({ why }) => why !== REQUIRED_WHY).map(({ field }) => field.label),
    note: reasons.get(NOTE_KEY) ?? null,
    timings,
  });
  return left
    .filter(({ field }) => (field.required && !field.value) || consents.has(keyOf(field)))
    .map(({ field }) => field.label);
}

const humanCheck = () =>
  [...document.querySelectorAll("iframe")].some(
    (frame) =>
      CHECK_FRAME.test(frame.src) &&
      !frame.src.includes("size=invisible") &&
      !frame.closest(".grecaptcha-badge") &&
      frame.checkVisibility(SHOWN) &&
      frame.getBoundingClientRect().width > 0,
  );

const labelOf = (element: HTMLElement) =>
  (element instanceof HTMLInputElement ? element.value : element.innerText).trim();

function submitButton(): HTMLElement | null {
  const buttons = [
    ...document.querySelectorAll<HTMLButtonElement | HTMLInputElement>(
      "button, input[type='submit']",
    ),
  ].filter(
    (element) =>
      !element.disabled && element.checkVisibility(SHOWN) && SUBMIT_TEXT.test(labelOf(element)),
  );
  const submits = buttons.filter((element) => SAYS_SUBMIT.test(labelOf(element)));
  const [only] = submits.length === 1 ? submits : buttons.length === 1 ? buttons : [];
  return only ?? null;
}

async function holdForYou(job: Job, panel: Panel, why: string): Promise<void> {
  await ask<object>({ type: "held", jobId: job.id, why });
  panel.say(`Auto-submit stopped: ${why}. Check it, then press Submit yourself.`);
}

function whyNotSend(left: string[]): string | null {
  if (left.length) {
    const named = left.slice(0, NAMED_LEFT).join("; ");
    const more = left.length > NAMED_LEFT ? ` and ${String(left.length - NAMED_LEFT)} more` : "";
    return `left for you: ${named}${more}`;
  }
  const note = reasons.get(NOTE_KEY);
  if (note) return note;
  return humanCheck() ? "the site shows a human check" : null;
}

async function confirmed(): Promise<string | null> {
  for (const start = performance.now(); since(start) < CONFIRM_WAIT_MS;) {
    if (shown.state === "applied") return null;
    if (humanCheck()) return "the site wants a human check after Submit";
    await sleep(POLL_MS);
  }
  return "the site didn't confirm it was sent";
}

async function autoSubmit(job: Job, panel: Panel, left: string[]): Promise<void> {
  const why = whyNotSend(left);
  const button = submitButton();
  if (why || !button) {
    await holdForYou(job, panel, why ?? "it couldn't find one clear Submit button");
    return;
  }
  const reply = await ask<Go>({ type: "submitting", jobId: job.id });
  if (failed(reply) || !reply.go) {
    panel.say("Auto-submit is off now. Check it, then press Submit yourself.");
    return;
  }
  panel.wait("Nothing is left for you. Sending it …");
  button.click();
  const problem = await confirmed();
  if (problem) {
    await holdForYou(job, panel, problem);
    return;
  }
  await ask<object>({ type: "sent", jobId: job.id });
}

async function fill(job: Job, panel: Panel, sending = false): Promise<void> {
  mark("filling");
  panel.wait("Reading the form …");
  let fields = await timed("wait for form", waitForForm());
  if (!fields.length) {
    mark("filled", { fields: [], forYou: [] });
    panel.say("No application form on this page.");
    return;
  }
  const resume = resumeLoader(job);
  for (let round = 0; round < MAX_ROUNDS && fields.some(needsWork); round += 1) {
    const problem = await fillRound(job, fields, resume, panel);
    if (problem) {
      mark("broken", { error: problem });
      panel.say(problem === "offline" ? "TruApply isn't running." : `Couldn't fill: ${problem}`);
      if (sending)
        await ask<object>({ type: "held", jobId: job.id, why: `couldn't fill: ${problem}` });
      return;
    }
    await sleep(SETTLE_MS);
    fields = readFields();
  }
  for (const field of fields) if (filled.has(field.id)) recommit(field);
  await sleep(SETTLE_MS);
  const left = finish(readFields(), panel);
  watch(job, panel);
  if (sending) await autoSubmit(job, panel, left);
}

const FORM_LOOK_MS = 5000;
const RESUME_UPLOAD = "input[type='file']";

async function whatPage(): Promise<"form" | "thanks" | "other"> {
  for (const start = performance.now(); since(start) < FORM_LOOK_MS;) {
    if (document.querySelector(RESUME_UPLOAD)) return "form";
    if (isThankYou()) return "thanks";
    await sleep(POLL_MS);
  }
  return "other";
}
const PREPARE_POLL_MS = 3000;
const PREPARE_WAIT_MS = 300_000;
const WAITING = new Set(["new", "scored"]);

const lookUp = () => ask<{ job: Job | null }>({ type: "job", url: location.href });

const day = (stamp: string) =>
  new Date(stamp).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

async function prepared(job: Job): Promise<Job> {
  for (let waited = 0; waited < PREPARE_WAIT_MS; waited += PREPARE_POLL_MS) {
    await sleep(PREPARE_POLL_MS);
    const found = await lookUp();
    if (!failed(found) && found.job && !WAITING.has(found.job.status)) return found.job;
  }
  return job;
}

async function add(panel: Panel): Promise<void> {
  panel.wait("Reading this job …");
  const reply = await ask<Added>({ type: "add", url: location.href, ...(await readPage()) });
  if (failed(reply)) {
    mark("broken", { error: reply.error });
    panel.say(`Couldn't add it: ${reply.error}`);
    return;
  }
  panel.show(reply.job);
  if (!WAITING.has(reply.job.status)) {
    await show(reply.job, panel);
    return;
  }
  mark("adding");
  panel.wait(
    reply.preparing
      ? "Added. Scoring it and tailoring your resume, about a minute …"
      : "Added. A run is going; it's prepared right after.",
  );
  const job = await prepared(reply.job);
  panel.show(job);
  await show(job, panel);
}

async function show(job: Job, panel: Panel, sending = false): Promise<void> {
  const wanted = job.status === "ready" || (clicked && job.status !== "applied");
  const page = wanted ? await whatPage() : "other";
  if (page === "form" || (clicked && wanted && page === "other")) {
    await fill(job, panel, sending);
    return;
  }
  if (sending) await ask<object>({ type: "held", jobId: job.id, why: "no application form here" });
  if (page === "thanks") {
    await markApplied(job, panel, await savedAnswers(job));
    return;
  }
  mark("shown", { status: job.status });
  const said: Record<string, string> = {
    ready: "Ready. Your tailored resume is saved. Open the application form to fill it.",
    applied: `You applied to this job on ${day(job.updatedAt)}.`,
    skipped: "TruApply skipped this job. See why in your tracker.",
    dismissed: "You dismissed this job.",
    closed: "This job is closed.",
  };
  panel.say(said[job.status] ?? "Not ready yet: its resume isn't tailored.");
  if (WAITING.has(job.status) || job.status === "skipped") {
    panel.offer("Tailor my resume for it", () => void add(panel));
  } else if (job.status === "ready") {
    panel.offer("Fill this form", () => void fill(job, panel));
  }
}

async function main(): Promise<void> {
  if (document.documentElement.dataset.truapply) return;
  mark("loading");
  stayOnPage(restore);
  for (const name of ["input", "change", "pointerdown"]) {
    document.addEventListener(name, noteTouch, true);
  }
  const found = await lookUp();
  if (failed(found)) {
    mark("offline");
    openPanel(null).say("TruApply isn't running. Start it, then reload this page.");
    return;
  }
  if (!found.job) {
    mark("unknown");
    const panel = openPanel(null);
    if (clicked) {
      await add(panel);
      return;
    }
    panel.say("This job isn't in TruApply yet.");
    panel.offer("Add to TruApply", () => void add(panel));
    return;
  }
  const asked = await ask<Sending>({ type: "sending" });
  const sending = !clicked && !failed(asked) && asked.jobId === found.job.id;
  await show(found.job, openPanel(found.job), sending);
}

void main();
