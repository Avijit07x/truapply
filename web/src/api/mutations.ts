import { type QueryKey, hashKey, useMutation, useQueryClient } from "@tanstack/react-query";
import { post } from "./client";
import { queries } from "./queries";
import type {
  Action,
  Dismissed,
  Linked,
  Named,
  JobDetail,
  Learned,
  Automatic,
  ResumeReplaced,
  ResumeUpload,
  RunChoice,
  RunState,
  Scoring,
  SendQueued,
  SettingsValues,
  SettingsView,
} from "./types";

type Request = readonly [path: string, body: object];

function useChange<Result, Input>(toRequest: (input: Input) => Request, storeAt?: QueryKey) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: Input) => post<Result>(...toRequest(input)),
    onSuccess: async (result) => {
      if (storeAt) {
        client.setQueryData(storeAt, result);
      }
      const kept = storeAt ? hashKey(storeAt) : null;
      await client.invalidateQueries({ predicate: (query) => query.queryHash !== kept });
    },
  });
}

export type JobChange = { action: Action; body?: object };

export function useJobChange(id: number) {
  return useChange<JobDetail, JobChange>(
    ({ action, body = {} }) => [`/api/jobs/${String(id)}/${action}`, body],
    queries.job(id).queryKey,
  );
}

export type LearnedChange = readonly [path: string, body?: object];

export function useLearnedChange() {
  return useChange<Learned, LearnedChange>(
    ([path, body = {}]) => [path, body],
    queries.learned().queryKey,
  );
}

export const learnedPaths = {
  add: "/api/rules",
  editRule: (id: number) => `/api/rules/${String(id)}/edit`,
  deleteRule: (id: number) => `/api/rules/${String(id)}/delete`,
  editAnswer: "/api/answers/edit",
  deleteAnswer: "/api/answers/delete",
  accept: (id: number) => `/api/suggestions/${String(id)}/accept`,
  dismiss: (id: number) => `/api/suggestions/${String(id)}/dismiss`,
} as const;

export function useRunStart() {
  return useChange<RunState, RunChoice>(
    (choice) => ["/api/runs/start", choice],
    queries.runs().queryKey,
  );
}

export function useRunStop() {
  return useChange<RunState, undefined>(() => ["/api/runs/stop", {}], queries.runs().queryKey);
}

export function useFindCompanies() {
  return useChange<RunState, undefined>(() => ["/api/companies/find", {}], queries.runs().queryKey);
}

export function useCheckArchive() {
  return useChange<{ going: boolean }, undefined>(() => ["/api/companies/archive", {}]);
}

export function useSendReady() {
  return useChange<SendQueued, undefined>(() => ["/api/autosend/queue", {}]);
}

export function useSetAutomatic() {
  return useChange<Automatic, boolean>((on) => ["/api/settings/automatic", { on }]);
}

export function useReplaceResume() {
  return useChange<ResumeReplaced, ResumeUpload>((upload) => ["/api/settings/resume", upload]);
}

export function useSaveSettings() {
  return useChange<SettingsView, SettingsValues>(
    (values) => ["/api/settings", values],
    queries.settings().queryKey,
  );
}

export type DismissMany = { ids: number[]; reason: string };

export function useDismissMany() {
  return useChange<Dismissed, DismissMany>(({ ids, reason }) => [
    "/api/jobs/dismiss",
    { ids, reason },
  ]);
}

export function useScoreMany() {
  return useChange<Scoring, readonly number[]>((ids) => ["/api/jobs/score", { ids }]);
}

export function useAddLink() {
  return useChange<Linked, string>((link) => ["/api/boards/link", { link }]);
}

export function useAddNames() {
  return useChange<Named, string>((names) => ["/api/boards/names", { names }]);
}
