import type { JobList, JobQuery } from "../../api/types";
import { jobsHref } from "../../domain/filters";
import { Button, ButtonLink } from "../../ui/Button";
import { ArrowLeft, ArrowRight } from "../../ui/icons";
import styles from "./Jobs.module.css";

type PageButtonProps = {
  query: JobQuery;
  page: number;
  enabled: boolean;
  next?: boolean;
  compact: boolean;
};

function PageButton({ query, page, enabled, next = false, compact }: PageButtonProps) {
  const word = next ? "Next" : "Previous";
  const label = compact ? <span className={styles.hidden}>{word}</span> : word;
  const icon = next ? undefined : <ArrowLeft size={12} />;
  const trail = next ? <ArrowRight size={12} /> : undefined;
  if (!enabled) {
    return (
      <Button disabled icon={icon}>
        {label}
        {trail}
      </Button>
    );
  }
  return (
    <ButtonLink to={jobsHref({ ...query, page: page > 1 ? page : undefined })} icon={icon}>
      {label}
      {trail}
    </ButtonLink>
  );
}

type PagerProps = { query: JobQuery; list: JobList; compact?: boolean };

export function Pager({ query, list, compact = false }: PagerProps) {
  const pages = Math.ceil(list.total / list.pageSize);
  if (pages <= 1) {
    return null;
  }
  const first = (list.page - 1) * list.pageSize + 1;
  const last = Math.min(list.page * list.pageSize, list.total);
  return (
    <nav className={styles.pager} aria-label="Pages">
      <span className={styles.range}>
        {first.toLocaleString()}–{last.toLocaleString()} of {list.total.toLocaleString()}
      </span>
      <PageButton query={query} page={list.page - 1} enabled={list.page > 1} compact={compact} />
      <PageButton
        query={query}
        page={list.page + 1}
        enabled={list.page < pages}
        compact={compact}
        next
      />
    </nav>
  );
}
