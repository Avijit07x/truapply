import { failed, type Reply } from "./messages";

const ROUND = "linkedin-read";
const NEXT = "linkedin-next";
const GIVE_UP = "linkedin-give-up";
const ROUND_EVERY_MINUTES = 240;
const FIRST_ROUND_MINUTES = 1;
const BETWEEN_SEARCHES_MINUTES = 0.5;
const PAGE_LIMIT_MINUTES = 3;
const STATE = "linkedinReading";
const BLANK = "about:blank";
const LAST = "linkedinLastRound";

const note = (outcome: string) =>
  chrome.storage.local.set({ [LAST]: { at: new Date().toISOString(), outcome } });

type Plan = { read: boolean; searches: string[]; left: number };
type State = { searches: string[]; next: number; tabId: number | null };
export type Ask = (path: string) => Promise<Reply<Plan>>;

async function state(): Promise<State | null> {
  const { [STATE]: saved } = await chrome.storage.local.get(STATE);
  return typeof saved === "object" && saved !== null ? (saved as State) : null;
}

const keep = (saved: State) => chrome.storage.local.set({ [STATE]: saved });

async function closeOpen(): Promise<void> {
  const saved = await state();
  if (saved?.tabId != null) await chrome.tabs.remove(saved.tabId).catch(() => undefined);
  await chrome.alarms.clear(GIVE_UP);
}

async function stop(): Promise<void> {
  await closeOpen();
  await chrome.storage.local.remove(STATE);
}

async function openNext(ask: Ask): Promise<void> {
  const saved = await state();
  const plan = await ask("/api/extension/linkedin-plan");
  if (!saved || failed(plan) || !plan.read || saved.next >= saved.searches.length) {
    await stop();
    return;
  }
  const url = saved.searches[saved.next] ?? "";
  const tab = await chrome.tabs.create({ url: BLANK, active: false });
  await keep({ ...saved, next: saved.next + 1, tabId: tab.id ?? null });
  if (tab.id !== undefined) await chrome.tabs.update(tab.id, { url });
  await chrome.alarms.create(GIVE_UP, { delayInMinutes: PAGE_LIMIT_MINUTES });
}

async function startRound(ask: Ask): Promise<void> {
  await stop();
  const plan = await ask("/api/extension/linkedin-plan").catch(() => null);
  if (!plan || failed(plan)) {
    await note("SatyaApply isn't running");
    return;
  }
  if (!plan.read || !plan.searches.length) {
    await note(plan.searches.length ? "done for today" : "reading is off");
    return;
  }
  await note("reading");
  await keep({ searches: plan.searches, next: 0, tabId: null });
  await openNext(ask);
}

export async function isReadingTab(tabId: number | undefined): Promise<boolean> {
  return tabId !== undefined && (await state())?.tabId === tabId;
}

export async function pageRead(tabId: number | undefined, blocked: boolean): Promise<void> {
  if (!(await isReadingTab(tabId))) return;
  if (blocked) {
    await note("stopped: LinkedIn showed no jobs");
    await stop();
    return;
  }
  await closeOpen();
  await chrome.alarms.create(NEXT, { delayInMinutes: BETWEEN_SEARCHES_MINUTES });
}

export function scheduleReading(ask: Ask): void {
  chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === ROUND) void startRound(ask);
    if (alarm.name === NEXT) void openNext(ask);
    if (alarm.name === GIVE_UP) void stop();
  });
  void chrome.alarms.get(ROUND).then((found) =>
    found
      ? undefined
      : chrome.alarms.create(ROUND, {
          delayInMinutes: FIRST_ROUND_MINUTES,
          periodInMinutes: ROUND_EVERY_MINUTES,
        }),
  );
}
