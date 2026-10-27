import type { Failure, Request } from "./messages";

const DEFAULT_PORT = 8765;
const OFFLINE = "offline";

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

function handle(request: Request): Promise<unknown> {
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
      });
    case "resume":
      return resume(request.jobId);
    case "applied":
      return post(`/api/extension/jobs/${String(request.jobId)}/applied`, { sent: request.sent });
  }
}

chrome.runtime.onMessage.addListener((message, _sender, reply) => {
  handle(message as Request).then(reply, () => {
    reply({ error: OFFLINE } satisfies Failure);
  });
  return true;
});

chrome.action.onClicked.addListener((tab) => {
  if (tab.id === undefined) return;
  const target = { tabId: tab.id };
  void chrome.scripting
    .executeScript({ target, files: ["network.js"], world: "MAIN" })
    .then(() => chrome.scripting.executeScript({ target, files: ["content.js"] }));
});
