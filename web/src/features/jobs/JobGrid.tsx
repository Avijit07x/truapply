import {
  type Header,
  type Row,
  type RowSelectionState,
  type SortingState,
  type Table,
  createColumnHelper,
  functionalUpdate,
  rowSelectionFeature,
  rowSortingFeature,
  tableFeatures,
  useTable,
} from "@tanstack/react-table";
import { type KeyboardEvent, useMemo, useState } from "react";
import { jobSearch } from "../../api/queries";
import type { JobList, JobQuery, JobRow, Sort, Summary } from "../../api/types";
import { place } from "../../components/JobList";
import { StatusDot } from "../../components/StatusDot";
import { defaultOrder, isSort, jobsHref } from "../../domain/filters";
import { STATUS } from "../../domain/status";
import { cx } from "../../lib/cx";
import { ago, when } from "../../lib/format";
import { Link, navigate } from "../../lib/router";
import { ChevronDown } from "../../ui/icons";
import { type FilterKind, HeaderFilter } from "./HeaderFilter";
import styles from "./Jobs.module.css";
import { ScoreCell, ScoringContext } from "./ScoreCell";
import { SelectionBar } from "./SelectionBar";
import { TableCheck } from "./TableCheck";

const features = tableFeatures({ rowSortingFeature, rowSelectionFeature });
type Features = typeof features;
type JobTable = Table<Features, JobRow>;

type Look = { label: string; className: string | undefined; filter?: FilterKind };

const LOOK: Partial<Record<string, Look>> = {
  select: { label: "Select", className: styles.selectColumn },
  title: { label: "Job", className: styles.jobColumn },
  company: { label: "Company", className: styles.companyColumn, filter: "company" },
  location: { label: "Location", className: styles.placeColumn, filter: "location" },
  score: { label: "Score", className: styles.scoreColumn, filter: "minScore" },
  status: { label: "Status", className: styles.statusColumn, filter: "status" },
  updated: { label: "Updated", className: styles.whenColumn },
};

function RowCheck({ row }: { row: Row<Features, JobRow> }) {
  const job = row.original;
  const allowed = row.getCanSelect();
  return (
    <TableCheck
      label={`Select ${job.title} at ${job.company}`}
      checked={row.getIsSelected()}
      disabled={!allowed}
      title={allowed ? undefined : `Can't pick: ${STATUS[job.status].label}`}
      onChange={row.getToggleSelectedHandler()}
    />
  );
}

const helper = createColumnHelper<Features, JobRow>();
const scoreColumn = helper.accessor("score", {
  sortDescFirst: true,
  cell: (info) => <ScoreCell job={info.row.original} />,
});
const columns = helper.columns([
  helper.display({ id: "select", cell: (info) => <RowCheck row={info.row} /> }),
  helper.accessor("title", {
    cell: (info) => (
      <>
        <Link to={`/jobs/${String(info.row.original.id)}`} className={styles.rowLink}>
          {info.getValue()}
        </Link>
        <span className={styles.sub}>{place(info.row.original)}</span>
      </>
    ),
  }),
  helper.accessor("company", {}),
  helper.accessor("location", {}),
  scoreColumn,
  helper.accessor("status", {
    enableSorting: false,
    cell: (info) => <StatusDot status={info.getValue()} labelClassName={styles.statusLabel} />,
  }),
  helper.accessor("updatedAt", {
    id: "updated",
    sortDescFirst: true,
    cell: (info) => (
      <time dateTime={info.getValue()} title={when(info.getValue())}>
        {ago(info.getValue())}
      </time>
    ),
  }),
]);
const siteColumns = columns.filter((column) => column !== scoreColumn);

function sortedHref(query: JobQuery, sort: Sort, desc: boolean): string {
  const order = desc ? "desc" : "asc";
  return jobsHref({
    ...query,
    sort: sort === "updated" ? undefined : sort,
    order: order === defaultOrder(sort) ? undefined : order,
    page: undefined,
  });
}

function ariaSort(header: Header<Features, JobRow>) {
  const sorted = header.column.getIsSorted();
  if (!sorted) {
    return undefined;
  }
  return sorted === "asc" ? "ascending" : "descending";
}

type Context = { query: JobQuery; counts: Summary["counts"]; total: number };

function SelectAll({ table }: { table: JobTable }) {
  const selectable = table.getRowModel().rows.some((row) => row.getCanSelect());
  return (
    <TableCheck
      label="Select every job on this page that can be dismissed"
      checked={table.getIsAllPageRowsSelected()}
      indeterminate={table.getIsSomePageRowsSelected()}
      disabled={!selectable}
      onChange={table.getToggleAllPageRowsSelectedHandler()}
    />
  );
}

function HeaderCell({
  header,
  table,
  context,
}: {
  header: Header<Features, JobRow>;
  table: JobTable;
  context: Context;
}) {
  const look = LOOK[header.column.id];
  const label = look?.label ?? header.column.id;
  if (header.column.id === "select") {
    return (
      <th scope="col" className={look?.className}>
        <SelectAll table={table} />
      </th>
    );
  }
  const sorted = header.column.getIsSorted();
  const pointing = sorted || header.column.getFirstSortDir();
  return (
    <th scope="col" className={look?.className} aria-sort={ariaSort(header)}>
      <span className={styles.headInner}>
        {header.column.getCanSort() ? (
          <button
            type="button"
            className={cx(styles.sortButton, sorted && styles.sorted)}
            onClick={header.column.getToggleSortingHandler()}
          >
            <span className={styles.headLabel}>{label}</span>
            <ChevronDown size={12} className={cx(styles.arrow, pointing === "asc" && styles.up)} />
          </button>
        ) : (
          <span className={styles.headLabel}>{label}</span>
        )}
        {look?.filter && <HeaderFilter kind={look.filter} label={label} {...context} />}
      </span>
    </th>
  );
}

function moveFocus(event: KeyboardEvent<HTMLDivElement>, table: JobTable): boolean {
  const rows = [...event.currentTarget.querySelectorAll<HTMLTableRowElement>("tbody tr")];
  const current = rows.findIndex((row) => row.contains(document.activeElement));
  const focusRow = (index: number) => {
    rows[index]?.querySelector<HTMLAnchorElement>("a")?.focus();
  };
  if (event.key === "ArrowDown") {
    focusRow(Math.min(current + 1, rows.length - 1));
    return true;
  }
  if (event.key === "ArrowUp") {
    focusRow(Math.max(current - 1, 0));
    return true;
  }
  const id = rows[current]?.dataset.rowId;
  if (event.key.toLowerCase() === "x" && id) {
    const row = table.getRow(id);
    if (row.getCanSelect()) {
      row.toggleSelected();
    }
    return true;
  }
  if (event.key === "Escape" && table.getIsSomeRowsSelected()) {
    table.resetRowSelection();
    return true;
  }
  return false;
}

type JobGridProps = Context & { list: JobList; pending: boolean };

export function JobGrid({ query, list, counts, total, pending }: JobGridProps) {
  const shown = jobSearch(query);
  const [picked, setPicked] = useState<{ shown: string; rows: RowSelectionState }>({
    shown,
    rows: {},
  });
  const rowSelection = picked.shown === shown ? picked.rows : {};
  const selectable = useMemo(
    () => new Set([...list.dismissable, ...list.scorable]),
    [list.dismissable, list.scorable],
  );
  const current = query.sort ?? "updated";
  const order = query.order ?? defaultOrder(current);
  const sorting = useMemo<SortingState>(
    () => [{ id: current, desc: order === "desc" }],
    [current, order],
  );
  const shownColumns = query.source ? siteColumns : columns;
  const table = useTable({
    features,
    columns: shownColumns,
    data: list.jobs,
    getRowId: (job) => String(job.id),
    manualSorting: true,
    enableSortingRemoval: false,
    enableMultiSort: false,
    enableRowSelection: (row) => selectable.has(row.original.status),
    state: { sorting, rowSelection },
    onSortingChange: (updater) => {
      const [next] = functionalUpdate(updater, sorting);
      if (next && isSort(next.id)) {
        navigate(sortedHref(query, next.id, next.desc));
      }
    },
    onRowSelectionChange: (updater) => {
      setPicked({ shown, rows: functionalUpdate(updater, rowSelection) });
    },
  });
  const context = { query, counts, total };
  const scoring = { scorable: new Set(list.scorable), scoring: new Set(list.scoring) };
  const selected = table.getSelectedRowIds().map(Number);
  return (
    <ScoringContext value={scoring}>
      <div
        className={cx(styles.tableWrap, pending && styles.pending)}
        aria-busy={pending || undefined}
        onKeyDown={(event) => {
          if (!event.metaKey && !event.ctrlKey && !event.altKey && moveFocus(event, table)) {
            event.preventDefault();
          }
        }}
      >
        <table className={cx(styles.table, list.total === 0 && styles.stretch)}>
          <thead>
            {table.getHeaderGroups().map((group) => (
              <tr key={group.id}>
                {group.headers.map((header) => (
                  <HeaderCell key={header.id} header={header} table={table} context={context} />
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {list.total === 0 && (
              <tr>
                <td colSpan={shownColumns.length} className={styles.noRows}>
                  {query.q ? `No jobs match “${query.q}”.` : "No jobs match these filters."}
                </td>
              </tr>
            )}
            {table.getRowModel().rows.map((row) => (
              <tr
                key={row.id}
                data-row-id={row.id}
                data-selected={row.getIsSelected() || undefined}
              >
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
      <SelectionBar
        ids={selected}
        reasons={list.dismissReasons}
        onClear={() => {
          table.resetRowSelection();
        }}
      />
    </ScoringContext>
  );
}
