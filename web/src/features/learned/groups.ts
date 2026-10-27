import type { SavedAnswer } from "../../api/types";

export type AnswerGroup = { title: string; written: boolean; answers: SavedAnswer[] };

const WRITTEN_LENGTH = 140;
const WRITTEN = "Written answers";
const OTHER = "Other";
const TOPICS: readonly { title: string; words: RegExp }[] = [
  { title: "Links", words: /github|linkedin|portfolio|website|twitter|\burl\b|\blink/i },
  {
    title: "About you",
    words:
      /name|e-?mail|phone|mobile|pronoun|gender|company|employer|location|city|reside|address/i,
  },
  {
    title: "Work and eligibility",
    words:
      /country|relocat|remote|visa|sponsor|authori[sz]|notice|salary|ctc|compensation|expected|on-?site|hybrid|payroll|start date|\bnyc\b|\bsf\b|canada|\bus\b/i,
  },
];
const ORDER = ["About you", "Links", "Work and eligibility", WRITTEN, OTHER];

function topicOf(answer: SavedAnswer): string {
  if (answer.answer.length > WRITTEN_LENGTH) {
    return WRITTEN;
  }
  return TOPICS.find(({ words }) => words.test(answer.question))?.title ?? OTHER;
}

export function grouped(answers: readonly SavedAnswer[]): AnswerGroup[] {
  const buckets = new Map<string, SavedAnswer[]>();
  for (const answer of answers) {
    const topic = topicOf(answer);
    buckets.set(topic, [...(buckets.get(topic) ?? []), answer]);
  }
  return ORDER.flatMap((title) => {
    const found = buckets.get(title);
    return found ? [{ title, written: title === WRITTEN, answers: found }] : [];
  });
}
