import { queryOptions } from "@tanstack/react-query";
import { get } from "./client";
import type {
  Board,
  JobDetail,
  JobList,
  JobQuery,
  Learned,
  RunLogLines,
  RunState,
  SettingsView,
  Summary,
  Workflow,
} from "./types";

const RUN_POLL_MS = 1_500;
const LIVE_POLL_MS = 4_000;
const NEW_JOBS_POLL_MS = 60_000;

const QUERY_KEYS = [
  "show",
  "status",
  "group",
  "q",
  "company",
  "location",
  "minScore",
  "source",
  "sort",
  "order",
  "page",
] as const;

export function jobSearch(query: JobQuery): string {
  const params = new URLSearchParams();
  for (const key of QUERY_KEYS) {
    const value = query[key];
    if (value !== undefined) {
      params.set(key, String(value));
    }
  }
  const text = params.toString();
  return text ? `?${text}` : "";
}

export const queries = {
  newJobs: (seen: Record<string, string>) =>
    queryOptions({
      queryKey: ["new-jobs", seen],
      queryFn: ({ signal }) =>
        get<Record<string, number>>(
          `/api/new-jobs?${new URLSearchParams(seen).toString()}`,
          signal,
        ),
      refetchInterval: NEW_JOBS_POLL_MS,
    }),
  summary: () =>
    queryOptions({
      queryKey: ["summary"],
      queryFn: ({ signal }) => get<Summary>("/api/summary", signal),
      refetchInterval: (query) => (query.state.data?.run.running ? LIVE_POLL_MS : false),
    }),
  jobs: (query: JobQuery) =>
    queryOptions({
      queryKey: ["jobs", query],
      queryFn: ({ signal }) => get<JobList>(`/api/jobs${jobSearch(query)}`, signal),
    }),
  board: () =>
    queryOptions({
      queryKey: ["board"],
      queryFn: ({ signal }) => get<Board>("/api/board", signal),
    }),
  job: (id: number) =>
    queryOptions({
      queryKey: ["job", id],
      queryFn: ({ signal }) => get<JobDetail>(`/api/jobs/${String(id)}`, signal),
    }),
  workflow: () =>
    queryOptions({
      queryKey: ["workflow"],
      queryFn: ({ signal }) => get<Workflow>("/api/workflow", signal),
    }),
  learned: () =>
    queryOptions({
      queryKey: ["learned"],
      queryFn: ({ signal }) => get<Learned>("/api/learned", signal),
    }),
  runs: () =>
    queryOptions({
      queryKey: ["runs"],
      queryFn: ({ signal }) => get<RunState>("/api/runs", signal),
      refetchInterval: (query) => (query.state.data?.running ? RUN_POLL_MS : false),
    }),
  runLog: (name: string) =>
    queryOptions({
      queryKey: ["runs", "log", name],
      queryFn: ({ signal }) =>
        get<RunLogLines>(`/api/runs/log/${encodeURIComponent(name)}`, signal),
      staleTime: Infinity,
    }),
  settings: () =>
    queryOptions({
      queryKey: ["settings"],
      queryFn: ({ signal }) => get<SettingsView>("/api/settings", signal),
    }),
};
