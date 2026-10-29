import { Popover } from "@base-ui/react/popover";
import { useState } from "react";
import type { JobQuery, Summary } from "../../api/types";
import { jobsHref } from "../../domain/filters";
import { sourceLabel } from "../../domain/sources";
import { activeCount } from "../../domain/status";
import { navigate } from "../../lib/router";
import { ChevronDown, Filter } from "../../ui/icons";
import { type FilterChipsProps, barChoices, kept, statusChoices } from "./FilterChips";
import styles from "./Jobs.module.css";

type Choice = { key: string; label: string; count: number; to: string; on: boolean };

function Group({
  title,
  choices,
  pick,
}: {
  title: string;
  choices: Choice[];
  pick: (to: string) => void;
}) {
  return (
    <>
      <Popover.Title className={styles.popupTitle}>{title}</Popover.Title>
      <div className={styles.statusChoices} role="group" aria-label={title}>
        {choices.map((choice) => (
          <button
            key={choice.key}
            type="button"
            className={styles.choice}
            aria-pressed={choice.on}
            onClick={() => {
              pick(choice.to);
            }}
          >
            {choice.label}
            <span className={styles.choiceCount}>{choice.count.toLocaleString()}</span>
          </button>
        ))}
      </div>
    </>
  );
}

function siteChoices(summary: Summary, query: JobQuery): Choice[] {
  const { table } = query;
  const career = activeCount(summary.counts, summary.total);
  const everywhere = table ? query.sites === "all" : query.sites !== "career";
  return [
    {
      key: "every",
      label: "All sites",
      count: summary.sites.reduce(
        (sum, site) => sum + activeCount(site.counts, site.total),
        career,
      ),
      to: table ? jobsHref({ sites: "all", table }) : "/jobs",
      on: !query.source && everywhere,
    },
    {
      key: "career",
      label: "Career pages",
      count: career,
      to: table ? jobsHref({ table }) : jobsHref({ sites: "career" }),
      on: !query.source && !everywhere,
    },
    ...summary.sites.map((site) => ({
      key: site.source,
      label: sourceLabel(site.source),
      count: activeCount(site.counts, site.total),
      to: jobsHref({ source: site.source, table }),
      on: query.source === site.source,
    })),
  ];
}

function showChoices(props: FilterChipsProps): Choice[] {
  const { query, total } = props;
  const more = statusChoices(props).map((choice) => ({
    ...choice,
    on: choice.key === query.status,
  }));
  if (query.table) {
    return [...barChoices(props).map((chip) => ({ ...chip, key: chip.label })), ...more];
  }
  const all = {
    key: "all",
    label: "All, even skipped",
    count: total,
    to: jobsHref({ ...kept(query), show: "all" }),
    on: query.show === "all" && !query.status && !query.group,
  };
  return [all, ...more];
}

export function JobsFilter({ summary, ...props }: FilterChipsProps & { summary: Summary }) {
  const [open, setOpen] = useState(false);
  const { query } = props;
  const pick = (to: string) => {
    navigate(to);
    setOpen(false);
  };
  const sites = siteChoices(summary, query);
  const shown = showChoices(props);
  const narrowed =
    Boolean(query.source) ||
    (query.table ? query.sites === "all" : query.sites === "career") ||
    Boolean(query.status ?? query.group ?? query.show);
  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger className={styles.menuButton} aria-current={narrowed ? "true" : undefined}>
        <Filter size={14} />
        Filter
        <ChevronDown size={10} />
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Positioner className={styles.positioner} sideOffset={6} align="end">
          <Popover.Popup className={styles.popup}>
            {summary.sites.length > 0 && <Group title="Site" choices={sites} pick={pick} />}
            <Group title="Show" choices={shown} pick={pick} />
          </Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
    </Popover.Root>
  );
}
