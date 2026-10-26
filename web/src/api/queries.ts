import { queryOptions } from "@tanstack/react-query";
import { get } from "./client";
import type {
  Board,
  JobDetail,
  JobFilter,
  JobList,
  Learned,
  RunLogLines,
  RunState,
  SettingsView,
  Summary,
  Workflow,
} from "./types";

const RUN_POLL_MS = 1_500;
const LIVE_POLL_MS = 4_000;

function search(filter: JobFilter): string {
  const params = new URLSearchParams();
  if (filter.status) {
    params.set("status", filter.status);
  }
  if (filter.group) {
    params.set("group", filter.group);
  }
  const text = params.toString();
  return text ? `?${text}` : "";
}

export const queries = {
  summary: () =>
    queryOptions({
      queryKey: ["summary"],
      queryFn: ({ signal }) => get<Summary>("/api/summary", signal),
      refetchInterval: (query) => (query.state.data?.run.running ? LIVE_POLL_MS : false),
    }),
  jobs: (filter: JobFilter) =>
    queryOptions({
      queryKey: ["jobs", filter],
      queryFn: ({ signal }) => get<JobList>(`/api/jobs${search(filter)}`, signal),
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
