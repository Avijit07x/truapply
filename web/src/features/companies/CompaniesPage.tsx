import { useSuspenseQueries } from "@tanstack/react-query";
import {
  type Header,
  type SortingState,
  createColumnHelper,
  createPaginatedRowModel,
  createSortedRowModel,
  rowPaginationFeature,
  rowSortingFeature,
  sortFn_alphanumeric,
  sortFn_basic,
  tableFeatures,
  useTable,
} from "@tanstack/react-table";
import { useState } from "react";
import { useCheckArchive, useFindCompanies } from "../../api/mutations";
import { queries } from "../../api/queries";
import type { Companies, CompanyOrigin, CompanyRow, CompanySearch } from "../../api/types";
import { cx } from "../../lib/cx";
import { plural, when } from "../../lib/format";
import { Link, navigate, useLocation } from "../../lib/router";
import { Ago } from "../../ui/Ago";
import { PageHeader } from "../../ui/Blocks";
import { Button } from "../../ui/Button";
import { ExternalLink } from "../../ui/ExternalLink";
import { ChevronDown, Filter, Inbox, Search } from "../../ui/icons";
import { SearchBox } from "../../ui/SearchBox";
import { toast } from "../../ui/toasts";
import styles from "../jobs/Jobs.module.css";
import { ChipMenu } from "../jobs/ChipMenu";
import { Pager } from "../jobs/Pager";
import { AddNames } from "./AddNames";
import own from "./Companies.module.css";

const features = tableFeatures({
  rowPaginationFeature,
  paginatedRowModel: createPaginatedRowModel(),
  rowSortingFeature,
  sortedRowModel: createSortedRowModel(),
  sortFns: { alphanumeric: sortFn_alphanumeric, basic: sortFn_basic },
});
type Features = typeof features;

const PAGE_SIZE = 50;

const SITE: Record<CompanyRow["site"], string> = {
  greenhouse: "Greenhouse",
  lever: "Lever",
  ashby: "Ashby",
};
const ORIGIN: Record<CompanyOrigin, string> = {
  shared: "Came with the app",
  search: "Web search",
  link: "Your job link",
  name: "You named it",
  archive: "Web archive",
};
const EVERY: Record<CompanySearch, string> = {
  off: "web search is off",
  daily: "searches every day",
  weekly: "searches every week",
};
const FOUND = ["search", "archive", "shared", "yours"] as const;
type Found = (typeof FOUND)[number];
const FOUND_LABEL: Record<Found, string> = {
  search: ORIGIN.search,
  archive: ORIGIN.archive,
  shared: ORIGIN.shared,
  yours: "Added by you",
};
const YOURS: ReadonlySet<CompanyOrigin> = new Set(["link", "name"]);
const CHIPS = ["all", "closed"] as const;
const SHOWS = [...CHIPS, ...FOUND] as const;
type Show = (typeof SHOWS)[number];

const LOOK: Record<string, { label: string; className?: string }> = {
  company: { label: "Company" },
  site: { label: "Site", className: own.siteColumn },
  origin: { label: "How it was found", className: own.originColumn },
  jobs: { label: "Jobs for you", className: own.jobsColumn },
  addedAt: { label: "Added", className: own.whenColumn },
  checkedAt: { label: "Last checked", className: own.whenColumn },
};

function Moment({ iso }: { iso: string | null }) {
  return iso ? (
    <time dateTime={iso} title={when(iso)}>
      <Ago iso={iso} />
    </time>
  ) : (
    "Not yet"
  );
}

const helper = createColumnHelper<Features, CompanyRow>();
const columns = helper.columns([
  helper.accessor("company", {
    sortFn: "alphanumeric",
    cell: (info) => <ExternalLink href={info.row.original.url}>{info.getValue()}</ExternalLink>,
  }),
  helper.accessor("site", { sortFn: "basic", cell: (info) => SITE[info.getValue()] }),
  helper.accessor("origin", { sortFn: "basic", cell: (info) => ORIGIN[info.getValue()] }),
  helper.accessor("jobs", { sortFn: "basic", sortDescFirst: true }),
  helper.accessor("addedAt", {
    sortFn: "basic",
    sortDescFirst: true,
    cell: (info) => <Moment iso={info.getValue()} />,
  }),
  helper.accessor("checkedAt", {
    sortFn: "basic",
    sortDescFirst: true,
    cell: (info) => (info.row.original.closed ? "Closed" : <Moment iso={info.getValue()} />),
  }),
]);

function isShow(value: string | null): value is Show {
  return SHOWS.includes(value as Show);
}

function isKind(row: CompanyRow, show: Show): boolean {
  if (show === "all") return true;
  if (show === "closed") return row.closed;
  return show === "yours" ? YOURS.has(row.origin) : row.origin === show;
}

function shown(row: CompanyRow, show: Show, q: string): boolean {
  return isKind(row, show) && row.company.toLowerCase().includes(q.toLowerCase());
}

function count(rows: readonly CompanyRow[], show: Show): number {
  return rows.filter((row) => shown(row, show, "")).length;
}

function href(show: Show, q: string, page = 1): string {
  const params = new URLSearchParams();
  if (show !== "all") params.set("show", show);
  if (q) params.set("q", q);
  if (page > 1) params.set("page", String(page));
  const search = params.toString();
  return search ? `/companies?${search}` : "/companies";
}

function HeaderCell({ header }: { header: Header<Features, CompanyRow> }) {
  const look = LOOK[header.column.id];
  const sorted = header.column.getIsSorted();
  const pointing = sorted || header.column.getFirstSortDir();
  return (
    <th
      scope="col"
      className={look?.className}
      aria-sort={sorted ? (sorted === "asc" ? "ascending" : "descending") : undefined}
    >
      <span className={styles.headInner}>
        <button
          type="button"
          className={cx(styles.sortButton, sorted && styles.sorted)}
          onClick={header.column.getToggleSortingHandler()}
        >
          <span className={styles.headLabel}>{look?.label}</span>
          <ChevronDown size={12} className={cx(styles.arrow, pointing === "asc" && styles.up)} />
        </button>
      </span>
    </th>
  );
}

function FindMore({ running }: { running: boolean }) {
  const find = useFindCompanies();
  return (
    <Button
      icon={<Search size={14} />}
      busy={find.isPending}
      disabled={running}
      title={
        running
          ? "Wait for the run that's going to finish."
          : "Asks the AI to search the web for new companies' job pages. Starts a run."
      }
      onClick={() => {
        find.mutate(undefined, {
          onSuccess: () => {
            toast("Looking for new companies. Follow it on the Run page.");
          },
        });
      }}
    >
      Search with AI
    </Button>
  );
}

function CheckArchive({ going, last }: { going: boolean; last: string | null }) {
  const check = useCheckArchive();
  return (
    <Button
      title={`Reads a free public list of job pages. No AI, runs in the background.${last ? ` Last checked ${when(last)}.` : ""}`}
      icon={<Inbox size={14} />}
      busy={check.isPending || going}
      disabled={going}
      onClick={() => {
        check.mutate(undefined, {
          onSuccess: () => {
            toast(
              "Searching the web archive in the background. New companies show up here when it's done.",
            );
          },
        });
      }}
    >
      {going ? "Searching the web archive" : "Search the web archive"}
    </Button>
  );
}

function searchNote(search: Companies["search"]) {
  return search.every !== "off" && search.next
    ? `next search ${when(search.next)}`
    : EVERY[search.every];
}

export default function CompaniesPage() {
  const { url } = useLocation();
  const picked = url.searchParams.get("show");
  const show: Show = isShow(picked) ? picked : "all";
  const q = url.searchParams.get("q") ?? "";
  const [{ data }, { data: summary }] = useSuspenseQueries({
    queries: [queries.companies(), queries.summary()],
  });
  const [sorting, setSorting] = useState<SortingState>([{ id: "company", desc: false }]);
  const rows = data.companies.filter((row) => shown(row, show, q));
  const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const page = Math.min(pages, Math.max(1, Number(url.searchParams.get("page")) || 1));
  const table = useTable({
    features,
    columns,
    data: rows,
    getRowId: (row) => row.key,
    enableSortingRemoval: false,
    enableMultiSort: false,
    state: { sorting, pagination: { pageIndex: page - 1, pageSize: PAGE_SIZE } },
    onSortingChange: setSorting,
  });
  const all = data.companies;
  return (
    <div className={styles.page}>
      <PageHeader
        title="Companies"
        description={`${plural(count(all, "all") - count(all, "closed"), "company", "companies")} · ${searchNote(data.search)}`}
      />
      <div className={own.tools}>
        <SearchBox
          label="Search companies"
          placeholder="Search companies"
          value={q}
          onSearch={(next) => {
            navigate(href(show, next), true);
          }}
        />
        <ChipMenu
          icon={<Filter size={14} />}
          label="Filter"
          idle="Filter"
          title="Show"
          any="All companies"
          anyTo={href("all", q)}
          picked={show === "all" ? null : show}
          choices={[
            { key: "closed", label: "Closed", count: count(all, "closed"), to: href("closed", q) },
            ...FOUND.map((found) => ({
              key: found,
              label: `Found by: ${FOUND_LABEL[found]}`,
              count: count(all, found),
              to: href(found, q),
            })),
          ]}
        />
        <div className={own.actions}>
          <CheckArchive going={data.archive.going} last={data.archive.last} />
          <FindMore running={summary.run.running} />
          <AddNames />
        </div>
      </div>
      <div className={styles.tableWrap}>
        <table className={cx(styles.table, rows.length === 0 && styles.stretch)}>
          <thead>
            {table.getHeaderGroups().map((group) => (
              <tr key={group.id}>
                {group.headers.map((header) => (
                  <HeaderCell key={header.id} header={header} />
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={columns.length} className={styles.noRows}>
                  {q ? `No companies match “${q}”.` : "No companies here yet."}
                </td>
              </tr>
            )}
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id}>
                {row.getAllCells().map((cell) => (
                  <td key={cell.id} className={LOOK[cell.column.id]?.className}>
                    <table.FlexRender cell={cell} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <footer className={styles.footer}>
        <p className={styles.keys}>
          <span>
            Jobs for you counts the jobs it listed from that company, not counting skipped or closed
            ones. Change how often it searches in <Link to="/settings?tab=search">Settings</Link>.
          </span>
        </p>
        <Pager
          page={page}
          pageSize={PAGE_SIZE}
          total={rows.length}
          hrefOf={(next) => href(show, q, next)}
        />
      </footer>
    </div>
  );
}
