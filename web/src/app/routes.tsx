import { type ComponentType, use } from "react";
import { queries } from "../api/queries";
import { jobQuery } from "../domain/filters";
import type { PageProps } from "../lib/router";
import type { PageLayout } from "./Layout";
import { queryClient } from "./queryClient";

type Page = ComponentType<PageProps>;
type Module = { default: Page };
type Warm = (params: readonly string[], url: URL) => readonly Promise<unknown>[];
type Route = {
  pattern: RegExp;
  load: () => Promise<Module>;
  warm: Warm;
  layout: PageLayout;
  Page: Page;
};
type Options = { warm?: Warm; layout?: PageLayout };

const NOTHING: Warm = () => [];

function page(
  pattern: RegExp,
  importer: () => Promise<Module>,
  { warm = NOTHING, layout = "page" }: Options = {},
): Route {
  let ready: Module | null = null;
  let loading: Promise<Module> | null = null;
  const load = (): Promise<Module> => {
    if (loading === null) {
      loading = importer();
      loading.then(
        (module) => {
          ready = module;
        },
        () => {
          loading = null;
        },
      );
    }
    return loading;
  };
  function Page(props: PageProps) {
    const { default: Loaded } = ready ?? use(load());
    return <Loaded {...props} />;
  }
  return { pattern, load, warm, layout, Page };
}

const ROUTES: readonly Route[] = [
  page(/^\/$/, () => import("../features/home/HomePage"), {
    layout: "fit",
    warm: () => [
      queryClient.query(queries.summary()),
      queryClient.query(queries.board()),
      queryClient.query(queries.workflow()),
    ],
  }),
  page(/^\/board$/, () => import("../features/board/BoardPage"), {
    layout: "fit",
    warm: () => [queryClient.query(queries.board())],
  }),
  page(/^\/workflow$/, () => import("../features/workflow/WorkflowPage"), {
    layout: "bleed",
    warm: () => [queryClient.query(queries.workflow())],
  }),
  page(/^\/jobs$/, () => import("../features/jobs/JobsPage"), {
    layout: "fit",
    warm: (_params, url) => [
      queryClient.query(queries.summary()),
      queryClient.query(queries.jobs(jobQuery(url.searchParams))),
    ],
  }),
  page(/^\/sites\/([a-z_]+)$/, () => import("../features/jobs/JobsPage"), {
    layout: "fit",
    warm: (params, url) => [
      queryClient.query(queries.summary()),
      queryClient.query(queries.jobs({ ...jobQuery(url.searchParams), source: params[0] })),
    ],
  }),
  page(/^\/jobs\/(\d+)$/, () => import("../features/job/JobPage"), {
    warm: (params) => [queryClient.query(queries.job(Number(params[0])))],
  }),
  page(/^\/runs$/, () => import("../features/runs/RunsPage"), {
    layout: "fit",
    warm: () => [queryClient.query(queries.runs())],
  }),
  page(/^\/runs\/(\d{8}-\d{6}-\d{6}\.log)$/, () => import("../features/runs/RunLogPage"), {
    layout: "fit",
    warm: (params) => [queryClient.query(queries.runLog(params[0] ?? ""))],
  }),
  page(/^\/learned$/, () => import("../features/learned/LearnedPage"), {
    layout: "fit",
    warm: () => [queryClient.query(queries.learned())],
  }),
  page(/^\/settings$/, () => import("../features/settings/SettingsPage"), {
    layout: "fit",
    warm: () => [queryClient.query(queries.settings())],
  }),
];

function match(path: string): { route: Route; params: string[] } | null {
  for (const route of ROUTES) {
    const found = route.pattern.exec(path);
    if (found) {
      return { route, params: found.slice(1) };
    }
  }
  return null;
}

export function findRoute(
  path: string,
): { Page: Page; params: string[]; layout: PageLayout } | null {
  const found = match(path);
  return found
    ? { Page: found.route.Page, params: found.params, layout: found.route.layout }
    : null;
}

export function preload(to: string): Promise<unknown> {
  const url = new URL(to, window.location.origin);
  const found = match(url.pathname);
  if (!found) {
    return Promise.resolve();
  }
  return Promise.allSettled([found.route.load(), ...found.route.warm(found.params, url)]);
}
