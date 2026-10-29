import { sourceLabel } from "../domain/sources";

export const PAGE_NAMES = {
  "/": "Today",
  "/jobs": "Jobs",
  "/jobs/table": "All jobs",
  "/companies": "Companies",
  "/runs": "Activity",
  "/learned": "Learned",
  "/settings": "Settings",
  "/setup": "Set up",
} as const;

const SITE_PAGE = /^\/sites\/([a-z_]+)(\/table)?$/;

export const sitePage = (source: string) => `/sites/${source}`;

export function pageName(path: string): string | undefined {
  const site = SITE_PAGE.exec(path)?.[1];
  return site ? `${sourceLabel(site)} jobs` : (PAGE_NAMES as Record<string, string>)[path];
}
