const SOURCE_LABEL: Record<string, string> = {
  career_pages: "Company careers page",
  linkedin: "LinkedIn",
  naukri: "Naukri",
  indeed: "Indeed",
  wellfound: "Wellfound",
  manual: "Added by you",
};

export function sourceLabel(source: string): string {
  return SOURCE_LABEL[source] ?? source;
}
