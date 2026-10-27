import { sourceLabel } from "../domain/sources";

export const PAGE_NAMES = {
  "/": "Home",
  "/board": "Board",
  "/workflow": "Workflow",
  "/jobs": "Career jobs",
  "/runs": "Run",
  "/learned": "Learned",
  "/settings": "Settings",
} as const;

const SITE_PAGE = /^\/sites\/([a-z_]+)$/;

export const sitePage = (source: string) => `/sites/${source}`;

export function pageName(path: string): string | undefined {
  const site = SITE_PAGE.exec(path)?.[1];
  return site ? `${sourceLabel(site)} jobs` : (PAGE_NAMES as Record<string, string>)[path];
}
