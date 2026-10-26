import { QueryErrorResetBoundary } from "@tanstack/react-query";
import { Suspense, useEffect } from "react";
import { useLocation } from "../lib/router";
import { ErrorBoundary } from "../ui/ErrorBoundary";
import { PageSkeleton } from "../ui/PageSkeleton";
import { Layout } from "./Layout";
import { NotFound } from "./NotFound";
import { findRoute } from "./routes";

export function App() {
  const { url } = useLocation();
  const path = url.pathname;
  const found = findRoute(path);
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [path]);
  return (
    <Layout path={path} bleed={found?.bleed ?? false}>
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
