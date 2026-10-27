export const PAGE_NAMES = {
  "/": "Home",
  "/board": "Board",
  "/workflow": "Workflow",
  "/jobs": "All jobs",
  "/runs": "Run",
  "/learned": "Learned",
  "/settings": "Settings",
} as const;

export const pageName = (path: string): string | undefined =>
  (PAGE_NAMES as Record<string, string>)[path];
