import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { queries } from "../api/queries";

const SELF_REFRESHING = new Set(["summary", "runs"]);

export function useLiveRefresh(): boolean {
  const client = useQueryClient();
  const { data, dataUpdatedAt } = useQuery(queries.summary());
  const running = data?.run.running ?? false;
  const wasRunning = useRef(running);
  useEffect(() => {
    if (running || wasRunning.current) {
      void client.invalidateQueries({
        predicate: (query) =>
          query.queryKey.length > 1 || !SELF_REFRESHING.has(String(query.queryKey[0])),
      });
    }
    wasRunning.current = running;
  }, [client, running, dataUpdatedAt]);
  return running;
}
