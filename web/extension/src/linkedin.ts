import { clean } from "./fields";
import { press, sleep } from "./fill";
import type { Posting } from "./messages";

const CARD = '[componentkey^="job-card-component-ref-"]';
const CARD_PREFIX = "job-card-component-ref-";
const VERIFIED = /\s*\(Verified job\)\s*$/i;
const ABOUT = /^\s*About the job\s*/i;
const DESCRIPTION_WAIT_MS = 5000;
const BETWEEN_JOBS_MS = 1000;
const STEP_MS = 200;

export type Listing = { url: string; posting: Posting };

export const isLinkedInSearch = () =>
  /(^|\.)linkedin\.com$/.test(location.hostname) && location.pathname.startsWith("/jobs/search");

function shownTexts(node: Node): string[] {
  if (node.nodeType === Node.TEXT_NODE)
    return clean(node.textContent) ? [clean(node.textContent)] : [];
  if (node instanceof Element && node.getAttribute("aria-hidden") === "true") return [];
  return [...node.childNodes].flatMap(shownTexts);
}

export function jobCards(): HTMLElement[] {
  return [...document.querySelectorAll<HTMLElement>(CARD)].filter(
    (card) => !card.parentElement?.closest(CARD),
  );
}

const cardId = (card: HTMLElement) =>
  (card.getAttribute("componentkey") ?? "").slice(CARD_PREFIX.length);

async function description(id: string): Promise<string> {
  for (let waited = 0; waited < DESCRIPTION_WAIT_MS; waited += STEP_MS) {
    const pane = document.querySelector(`[componentkey="JobDetails_AboutTheJob_${id}"]`);
    if (pane) return clean(pane.textContent).replace(ABOUT, "");
    await sleep(STEP_MS);
  }
  return "";
}

async function listing(card: HTMLElement): Promise<Listing | null> {
  const id = cardId(card);
  const [title = "", company = "", place = ""] = shownTexts(card);
  if (!id || !title || !company) return null;
  press(card);
  return {
    url: `https://www.linkedin.com/jobs/view/${id}/`,
    posting: {
      title: title.replace(VERIFIED, ""),
      company,
      location: place,
      description: await description(id),
    },
  };
}

export async function readListings(): Promise<Listing[]> {
  const found: Listing[] = [];
  for (const card of jobCards()) {
    const item = await listing(card);
    if (item) found.push(item);
    await sleep(BETWEEN_JOBS_MS);
  }
  return found;
}
