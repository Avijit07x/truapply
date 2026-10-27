import { clean } from "./fields";
import type { Posting } from "./messages";

const MOST_TEXT = 30_000;

type Found = Record<string, unknown>;

const isObject = (value: unknown): value is Found =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const textOf = (value: unknown): string => (typeof value === "string" ? clean(value) : "");

const plainText = (html: string) =>
  clean(new DOMParser().parseFromString(html, "text/html").body.textContent);

function postings(value: unknown): Found[] {
  if (Array.isArray(value)) return value.flatMap(postings);
  if (!isObject(value)) return [];
  const type = value["@type"];
  const own = type === "JobPosting" || (Array.isArray(type) && type.includes("JobPosting"));
  return [...(own ? [value] : []), ...postings(value["@graph"])];
}

function place(posting: Found): string {
  const where = [posting.jobLocation].flat()[0];
  const address = isObject(where) && isObject(where.address) ? where.address : {};
  const parts = ["addressLocality", "addressRegion", "addressCountry"].map((key) => {
    const part = address[key];
    return isObject(part) ? textOf(part.name) : textOf(part);
  });
  return parts.filter(Boolean).join(", ");
}

function fromData(): Posting | null {
  for (const script of document.querySelectorAll('script[type="application/ld+json"]')) {
    let data: unknown;
    try {
      data = JSON.parse(script.textContent);
    } catch {
      continue;
    }
    const [posting] = postings(data);
    if (!posting) continue;
    const company = isObject(posting.hiringOrganization) ? posting.hiringOrganization.name : "";
    return {
      title: textOf(posting.title),
      company: textOf(company),
      location: place(posting),
      description: plainText(textOf(posting.description)),
    };
  }
  return null;
}

const DATA_WAIT_MS = 4000;
const STEP_MS = 250;

const pause = (ms: number) => new Promise((done) => setTimeout(done, ms));

export async function readPage(): Promise<{ posting?: Posting; text: string }> {
  let posting = fromData();
  for (let waited = 0; !posting && waited < DATA_WAIT_MS; waited += STEP_MS) {
    await pause(STEP_MS);
    posting = fromData();
  }
  const text = posting?.title && posting.company ? "" : document.body.innerText.slice(0, MOST_TEXT);
  return posting ? { posting, text } : { text };
}
