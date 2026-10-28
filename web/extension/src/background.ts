import type { Failure, Request } from "./messages";

const DEFAULT_PORT = 8765;
const OFFLINE = "offline";
const SEND_ALARM = "send";
const SEND_EVERY_MINUTES = 1;
const SENDING = "sending";
const CLOSED_TAB = "you closed its tab before it was sent";

type Sending = { tabId: number; jobId: number };

async function base(): Promise<string> {
  const { port } = await chrome.storage.local.get("port");
  return `http://127.0.0.1:${typeof port === "number" ? String(port) : String(DEFAULT_PORT)}`;
}

async function post(path: string, body: unknown): Promise<unknown> {
  const response = await fetch((await base()) + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data: unknown = await response.json();
  if (response.ok) return data;
  const text = typeof data === "object" && data !== null && "error" in data ? data.error : "";
  return {
    error: typeof text === "string" && text ? text : `the app said ${String(response.status)}`,
  };
}

async function resume(jobId: number): Promise<unknown> {
  const response = await fetch(`${await base()}/jobs/${String(jobId)}/resume.pdf`);
  if (!response.ok) return { error: "no resume file for this job" };
  const bytes = new Uint8Array(await response.arrayBuffer());
  let binary = "";
  bytes.forEach((byte) => (binary += String.fromCharCode(byte)));
  return { data: btoa(binary) };
}

async function sending(): Promise<Sending | null> {
  const stored = (await chrome.storage.session.get(SENDING))[SENDING];
  return stored && typeof stored === "object" ? (stored as Sending) : null;
}

const doneSending = () => chrome.storage.session.remove(SENDING);

async function tabOpen(tabId: number): Promise<boolean> {
  return chrome.tabs.get(tabId).then(
    () => true,
    () => false,
  );
}

async function sendNext(): Promise<void> {
  const current = await sending();
  if (current && (await tabOpen(current.tabId))) return;
  if (current) await doneSending();
  const reply = await post("/api/extension/send/next", {});
  const job = reply && typeof reply === "object" && "job" in reply ? reply.job : null;
  if (!job || typeof job !== "object" || !("id" in job) || !("url" in job)) return;
  const tab = await chrome.tabs.create({ url: String(job.url), active: true });
  if (tab.id !== undefined) {
    await chrome.storage.session.set({ [SENDING]: { tabId: tab.id, jobId: Number(job.id) } });
  }
}

async function whoIsSending(tabId: number | undefined): Promise<unknown> {
  const current = await sending();
  return { jobId: current && current.tabId === tabId ? current.jobId : null };
}

async function finished(jobId: number, tabId: number | undefined, close: boolean) {
  const current = await sending();
  if (current?.jobId !== jobId) return { done: true };
  await doneSending();
  if (close && tabId !== undefined) await chrome.tabs.remove(tabId);
  void sendNext().catch(() => undefined);
  return { done: true };
}

function handle(request: Request, tabId: number | undefined): Promise<unknown> {
  switch (request.type) {
    case "job":
      return post("/api/extension/job", { url: request.url });
    case "answers":
      return post(`/api/extension/jobs/${String(request.jobId)}/answers`, {
        fields: request.fields,
        ai: request.ai,
      });
    case "add":
      return post("/api/extension/add", {
        url: request.url,
        posting: request.posting,
        text: request.text,
        prepare: request.prepare,
      });
    case "resume":
      return resume(request.jobId);
    case "applied":
      return post(`/api/extension/jobs/${String(request.jobId)}/applied`, { sent: request.sent });
    case "sending":
      return whoIsSending(tabId);
    case "submitting":
      return post(`/api/extension/jobs/${String(request.jobId)}/submitting`, {});
    case "held":
      return post(`/api/extension/jobs/${String(request.jobId)}/held`, { why: request.why }).then(
        () => finished(request.jobId, tabId, false),
      );
    case "sent":
      return finished(request.jobId, tabId, true);
    case "wake":
      return sendNext().then(() => ({ woken: true }));
  }
}

chrome.runtime.onMessage.addListener((message, sender, reply) => {
  handle(message as Request, sender.tab?.id).then(reply, () => {
    reply({ error: OFFLINE } satisfies Failure);
  });
  return true;
});

const markClicked = () => {
  (globalThis as { truapplyClicked?: boolean }).truapplyClicked = true;
};

chrome.action.onClicked.addListener((tab) => {
  if (tab.id === undefined) return;
  const target = { tabId: tab.id };
  void chrome.scripting
    .executeScript({ target, func: markClicked })
    .then(() => chrome.scripting.executeScript({ target, files: ["network.js"], world: "MAIN" }))
    .then(() => chrome.scripting.executeScript({ target, files: ["content.js"] }));
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === SEND_ALARM) void sendNext().catch(() => undefined);
});

chrome.tabs.onRemoved.addListener((tabId) => {
  void sending().then(async (current) => {
    if (current?.tabId !== tabId) return;
    await doneSending();
    await post(`/api/extension/jobs/${String(current.jobId)}/held`, { why: CLOSED_TAB });
  });
});

void chrome.alarms.get(SEND_ALARM).then((alarm) => {
  if (!alarm) void chrome.alarms.create(SEND_ALARM, { periodInMinutes: SEND_EVERY_MINUTES });
});
