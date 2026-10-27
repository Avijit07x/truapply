import { jobSearch } from "../api/queries";
import type { JobQuery, Order, Sort } from "../api/types";
import { sitePage } from "../lib/pages";
import { isGroup } from "./groups";
import { isStatus } from "./status";

const SORTS: readonly Sort[] = ["updated", "score", "title", "company", "location"];
const NEWEST_FIRST: readonly Sort[] = ["updated", "score"];
const LAST_PAGE = 999_999;
const HIGHEST_SCORE = 100;

export function isSort(value: string | null): value is Sort {
  return SORTS.some((sort) => sort === value);
}

function isOrder(value: string | null): value is Order {
  return value === "asc" || value === "desc";
}

export function defaultOrder(sort: Sort): Order {
  return NEWEST_FIRST.includes(sort) ? "desc" : "asc";
}

function words(value: string | null): string | undefined {
  const trimmed = value?.trim() ?? "";
  return trimmed === "" ? undefined : trimmed;
}

export function jobQuery(params: URLSearchParams): JobQuery {
  const group = params.get("group");
  const status = params.get("status");
  const sort = params.get("sort");
  const order = params.get("order");
  const page = Number(params.get("page"));
  const minScore = Number(params.get("minScore"));
  return {
    show: params.get("show") === "all" ? "all" : undefined,
    group: isGroup(group) ? group : undefined,
    status: !isGroup(group) && isStatus(status) ? status : undefined,
    q: words(params.get("q")),
    company: words(params.get("company")),
    location: words(params.get("location")),
    minScore:
      Number.isInteger(minScore) && minScore > 0 && minScore <= HIGHEST_SCORE
        ? minScore
        : undefined,
    sort: isSort(sort) ? sort : undefined,
    order: isOrder(order) ? order : undefined,
    page: Number.isInteger(page) && page > 1 && page <= LAST_PAGE ? page : undefined,
  };
}

export function jobsHref({ source, ...query }: JobQuery): string {
  return `${source ? sitePage(source) : "/jobs"}${jobSearch(query)}`;
}
