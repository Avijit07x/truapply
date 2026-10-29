import type { JobList, JobQuery } from "../../api/types";
import { jobsHref } from "../../domain/filters";
import { Button, ButtonLink } from "../../ui/Button";
import { ArrowLeft, ArrowRight } from "../../ui/icons";
import styles from "./Jobs.module.css";

type PageButtonProps = { to: string | null; next?: boolean; compact: boolean };

function PageButton({ to, next = false, compact }: PageButtonProps) {
  const word = next ? "Next" : "Previous";
  const label = compact ? <span className={styles.hidden}>{word}</span> : word;
  const icon = next ? undefined : <ArrowLeft size={12} />;
  const trail = next ? <ArrowRight size={12} /> : undefined;
  if (to === null) {
    return (
      <Button disabled icon={icon}>
        {label}
        {trail}
      </Button>
    );
  }
  return (
    <ButtonLink to={to} icon={icon}>
      {label}
      {trail}
    </ButtonLink>
  );
}

type PagerProps = {
  page: number;
  pageSize: number;
  total: number;
  hrefOf: (page: number) => string;
  compact?: boolean;
};

export function Pager({ page, pageSize, total, hrefOf, compact = false }: PagerProps) {
  const pages = Math.ceil(total / pageSize);
  if (pages <= 1) {
    return null;
  }
  const first = (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, total);
  return (
    <nav className={styles.pager} aria-label="Pages">
      <span className={styles.range}>
        {first.toLocaleString()}–{last.toLocaleString()} of {total.toLocaleString()}
      </span>
      <PageButton to={page > 1 ? hrefOf(page - 1) : null} compact={compact} />
      <PageButton to={page < pages ? hrefOf(page + 1) : null} compact={compact} next />
    </nav>
  );
}

export function jobPages(query: JobQuery, list: JobList): PagerProps {
  return {
    page: list.page,
    pageSize: list.pageSize,
    total: list.total,
    hrefOf: (page) => jobsHref({ ...query, page: page > 1 ? page : undefined }),
  };
}
