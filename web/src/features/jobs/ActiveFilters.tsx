import type { JobQuery } from "../../api/types";
import { jobsHref } from "../../domain/filters";
import { Link } from "../../lib/router";
import { Close } from "../../ui/icons";
import styles from "./Jobs.module.css";

type Pill = { label: string; without: JobQuery };

function pills(query: JobQuery): Pill[] {
  const found: Pill[] = [];
  if (query.company) {
    found.push({ label: `Company: ${query.company}`, without: { ...query, company: undefined } });
  }
  if (query.location) {
    found.push({
      label: `Location: ${query.location}`,
      without: { ...query, location: undefined },
    });
  }
  if (query.minScore) {
    found.push({
      label: `Score ${String(query.minScore)}+`,
      without: { ...query, minScore: undefined },
    });
  }
  return found;
}

export function ActiveFilters({ query }: { query: JobQuery }) {
  const shown = pills(query);
  if (shown.length === 0) {
    return null;
  }
  const cleared = { ...query, company: undefined, location: undefined, minScore: undefined };
  return (
    <nav className={styles.activeFilters} aria-label="Filters in use">
      {shown.map(({ label, without }) => (
        <Link
          key={label}
          to={jobsHref({ ...without, page: undefined })}
          className={styles.filterPill}
          aria-label={`Remove filter ${label}`}
        >
          {label}
          <Close size={10} />
        </Link>
      ))}
      {shown.length > 1 && (
        <Link to={jobsHref({ ...cleared, page: undefined })} className={styles.clearFilters}>
          Clear filters
        </Link>
      )}
    </nav>
  );
}
