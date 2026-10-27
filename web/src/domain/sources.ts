const SOURCE_LABEL: Record<string, string> = {
  career_pages: "Careers page",
  linkedin: "LinkedIn",
  naukri: "Naukri",
  indeed: "Indeed",
  wellfound: "Wellfound",
  manual: "Added by you",
};

export const SOURCES = Object.keys(SOURCE_LABEL);

export const isSource = (value: string | null): value is string =>
  SOURCES.some((source) => source === value);

export function sourceLabel(source: string): string {
  return SOURCE_LABEL[source] ?? source;
}

export const listedOnly = (job: { source: string }) => job.source === "wellfound";
