import { useMutation, useQueryClient } from "@tanstack/react-query";
import { post } from "../../api/client";
import { queries } from "../../api/queries";
import type { Board, JobDetail, JobRow, Status } from "../../api/types";
import { toast } from "../../ui/toasts";

export type Move =
  { job: JobRow; to: "applied" } | { job: JobRow; to: "dismissed"; reason: string };

export function moveCard(board: Board, job: JobRow, to: Status): Board {
  const moved = { ...job, status: to };
  const columns = board.columns.map((column) => {
    if (column.status === job.status) {
      const jobs = column.jobs.filter((item) => item.id !== job.id);
      return { ...column, jobs, total: column.total - (column.jobs.length - jobs.length) };
    }
    if (column.status === to) {
      return { ...column, jobs: [moved, ...column.jobs], total: column.total + 1 };
    }
    return column;
  });
  return { ...board, columns };
}

function request(move: Move): [string, object] {
  const path = `/api/jobs/${String(move.job.id)}`;
  return move.to === "applied"
    ? [`${path}/finished`, {}]
    : [`${path}/dismiss`, { reason: move.reason }];
}

export function useMoveCard() {
  const client = useQueryClient();
  const { queryKey } = queries.board();
  return useMutation({
    mutationFn: (move: Move) => post<JobDetail>(...request(move)),
    onMutate: async (move) => {
      await client.cancelQueries({ queryKey });
      const previous = client.getQueryData(queryKey);
      client.setQueryData(queryKey, (board) => board && moveCard(board, move.job, move.to));
      return { previous };
    },
    onError: (_error, _move, context) => {
      if (context?.previous) {
        client.setQueryData(queryKey, context.previous);
      }
    },
    onSuccess: (job, move) => {
      client.setQueryData(queries.job(job.id).queryKey, job);
      toast(move.to === "applied" ? `Marked as applied to ${job.company}.` : "Dismissed.");
    },
    onSettled: () => client.invalidateQueries(),
  });
}
