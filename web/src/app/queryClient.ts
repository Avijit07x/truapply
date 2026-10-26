import { MutationCache, QueryClient } from "@tanstack/react-query";
import { RequestFailed, messageOf } from "../api/client";
import { toast } from "../ui/toasts";

const SERVER_ERRORS = 500;
const MAX_RETRIES = 2;

function retryable(failures: number, error: unknown): boolean {
  const status = error instanceof RequestFailed ? error.status : SERVER_ERRORS;
  return failures < MAX_RETRIES && (status === 0 || status >= SERVER_ERRORS);
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 5_000, retry: retryable },
    mutations: { retry: false },
  },
  mutationCache: new MutationCache({
    onError: (error) => {
      toast(messageOf(error), "error");
    },
  }),
});
