export type Kind =
  | "text"
  | "email"
  | "tel"
  | "number"
  | "url"
  | "date"
  | "textarea"
  | "select"
  | "radio"
  | "checkbox"
  | "checkboxes"
  | "file"
  | "combobox";

export type Field = {
  id: string;
  kind: Kind;
  label: string;
  required: boolean;
  options: string[];
  value: string;
  max_length: number | null;
};

export type Job = {
  id: number;
  title: string;
  company: string;
  score: number | null;
  status: string;
  updatedAt: string;
  resume: string | null;
};

export type Posting = { title: string; company: string; location: string; description: string };
export type Added = { job: Job; preparing: boolean };

export type ForYou = { id: string; label: string; why: string; consent: boolean };
export type Answers = {
  answers: { id: string; value: string }[];
  forYou: ForYou[];
  waiting: string[];
  note: string | null;
};
export type SentItem = { question: string; answer: string; kind: Kind; yours: boolean };
export type Resume = { data: string };

export type Request =
  | { type: "job"; url: string }
  | { type: "answers"; jobId: number; fields: Field[]; ai: boolean }
  | { type: "add"; url: string; posting?: Posting; text: string; prepare: boolean }
  | { type: "resume"; jobId: number }
  | { type: "applied"; jobId: number; sent: SentItem[] }
  | { type: "sending" }
  | { type: "submitting"; jobId: number }
  | { type: "held"; jobId: number; why: string }
  | { type: "sent"; jobId: number }
  | { type: "wake" };

export type Sending = { jobId: number | null };
export type Go = { go: boolean };

export type Failure = { error: string };
export type Reply<T> = T | Failure;

export const failed = <T>(reply: Reply<T>): reply is Failure =>
  typeof reply === "object" && reply !== null && "error" in reply;
