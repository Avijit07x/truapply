import { isDay, isWhen } from "./dates";
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

function isSites(value: string | null): value is "all" | "career" {
  return value === "all" || value === "career";
}

export function listQuery(query: JobQuery): JobQuery {
  const careerOnly = query.sites === "career" || query.group !== undefined || query.source;
  return { ...query, sites: careerOnly ? undefined : "all" };
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
  const sites = params.get("sites");
  const when = params.get("when");
  const from = params.get("from");
  const to = params.get("to");
  const status = params.get("status");
  const sort = params.get("sort");
  const order = params.get("order");
  const page = Number(params.get("page"));
  const minScore = Number(params.get("minScore"));
  return {
    show: params.get("show") === "all" ? "all" : undefined,
    sites: isSites(sites) ? sites : undefined,
    when: isWhen(when) ? when : undefined,
    from: when === "custom" && isDay(from) ? from : undefined,
    to: when === "custom" && isDay(to) ? to : undefined,
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

export function jobsHref({ source, table, ...query }: JobQuery): string {
  const page = source ? sitePage(source) : "/jobs";
  return `${table ? `${page}/table` : page}${jobSearch(query)}`;
}
