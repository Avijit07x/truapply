import { QueryErrorResetBoundary, useQuery } from "@tanstack/react-query";
import { Suspense, useEffect } from "react";
import { queries } from "../api/queries";
import { navigate, useLocation } from "../lib/router";
import { ErrorBoundary } from "../ui/ErrorBoundary";
import { PageSkeleton } from "../ui/PageSkeleton";
import { Layout } from "./Layout";
import { NotFound } from "./NotFound";
import { findRoute } from "./routes";

const SETUP = "/setup";

export function App() {
  const { url } = useLocation();
  const path = url.pathname;
  const { data: summary } = useQuery(queries.summary());
  const locked = summary?.setupNeeded ?? false;
  const found = findRoute(locked ? SETUP : path);
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [path]);
  useEffect(() => {
    if (locked && path !== SETUP) navigate(SETUP, true);
    if (summary && !locked && path === SETUP) navigate("/", true);
  }, [locked, path, summary]);
  return (
    <Layout path={path} layout={found?.layout ?? "page"}>
      <QueryErrorResetBoundary>
        {({ reset }) => (
          <ErrorBoundary resetKey={path} onReset={reset}>
            <Suspense fallback={<PageSkeleton />}>
              {found ? <found.Page params={found.params} /> : <NotFound />}
            </Suspense>
          </ErrorBoundary>
        )}
      </QueryErrorResetBoundary>
    </Layout>
  );
}
