import { Handle, type Node, type NodeProps, Position } from "@xyflow/react";
import type { ComponentType } from "react";
import type { Group } from "../../api/types";
import { GROUP_TONE } from "../../domain/groups";
import { cx } from "../../lib/cx";
import { CountUp } from "../../ui/CountUp";
import { Check, type IconProps, Rows, Spark } from "../../ui/icons";
import type { Step, StepKind } from "./flow";
import styles from "./Workflow.module.css";

export type StepData = { step: Step; count: number | null; total: number; running: boolean };
export type OutcomeData = {
  group: Group;
  branch: string;
  title: string;
  count: number;
  total: number;
};
export type LaneData = { title: string };

export type StepNode = Node<StepData, "step">;
export type OutcomeNode = Node<OutcomeData, "outcome">;
export type LaneNode = Node<LaneData, "lane">;
export type FlowNode = StepNode | OutcomeNode | LaneNode;

const TAG: Record<StepKind, string> = {
  auto: "Automatic",
  question: "Question",
  jobs: "Your jobs",
  done: "Done",
};

const ICON: Record<Exclude<StepKind, "question">, ComponentType<IconProps>> = {
  auto: Spark,
  jobs: Rows,
  done: Check,
};

function Pins({ sides }: { sides: readonly ("top" | "left" | "bottom" | "right")[] }) {
  return sides.map((side) => (
    <Handle
      key={side}
      id={side}
      type={side === "top" || side === "left" ? "target" : "source"}
      position={
        { top: Position.Top, left: Position.Left, bottom: Position.Bottom, right: Position.Right }[
          side
        ]
      }
      isConnectable={false}
      className={styles.pin}
    />
  ));
}

function Tile({ kind }: { kind: StepKind }) {
  if (kind === "question") {
    return (
      <span className={cx(styles.tile, styles.questionTile)} aria-hidden="true">
        ?
      </span>
    );
  }
  const Icon = ICON[kind];
  return (
    <span className={styles.tile} aria-hidden="true">
      <Icon size={12} />
    </span>
  );
}

const MIN_SHARE = 4;
type Fill = "accent" | "good" | "warn" | "bad" | "auto" | "plain";

const FILL: Record<Fill, string | undefined> = {
  accent: styles.fillAccent,
  good: styles.fillGood,
  warn: styles.fillWarn,
  bad: styles.fillBad,
  auto: styles.fillAuto,
  plain: styles.fillPlain,
};
const STEP_FILL: Record<StepKind, Fill> = {
  auto: "auto",
  question: "plain",
  jobs: "accent",
  done: "good",
};

function Share({ part, total, fill }: { part: number; total: number; fill: Fill }) {
  if (part === 0 || total === 0) {
    return null;
  }
  const width = Math.max(MIN_SHARE, (part / total) * 100);
  return (
    <span className={styles.share} aria-hidden="true">
      <span className={cx(styles.shareFill, FILL[fill])} style={{ width: `${String(width)}%` }} />
    </span>
  );
}

export function StepCard({ data, selected }: NodeProps<StepNode>) {
  const { step, count, total, running } = data;
  const live = running && step.kind === "auto";
  return (
    <div
      className={cx(
        styles.card,
        styles[step.kind],
        step.group && styles.clickable,
        count === 0 && styles.quiet,
        selected && styles.selected,
      )}
    >
      <Pins sides={["top", "left", "bottom", "right"]} />
      <div className={styles.cardHead}>
        <Tile kind={step.kind} />
        <span className={cx(styles.tag, live && styles.liveTag)}>
          {live ? "Running" : TAG[step.kind]}
        </span>
        {count !== null && (
          <span className={styles.cardCount}>
            <CountUp value={count} />
            {step.countLabel && <small>{step.countLabel}</small>}
          </span>
        )}
      </div>
      <p className={styles.cardTitle}>{step.title}</p>
      {step.note && <p className={styles.cardNote}>{step.note}</p>}
      {count !== null && step.group !== "found" && (
        <Share part={count} total={total} fill={STEP_FILL[step.kind]} />
      )}
    </div>
  );
}

export function OutcomeCard({ data, selected }: NodeProps<OutcomeNode>) {
  const tone = GROUP_TONE[data.group] ?? "plain";
  return (
    <div
      className={cx(
        styles.outcome,
        styles.clickable,
        data.count === 0 && styles.quiet,
        selected && styles.selected,
      )}
    >
      <Pins sides={["left"]} />
      <span className={styles.outcomeHead}>
        <span className={styles.branch}>{data.branch}</span>
        <Share part={data.count} total={data.total} fill={tone} />
        <span className={styles.outcomeCount}>
          <CountUp value={data.count} />
        </span>
      </span>
      <span className={styles.outcomeRow}>
        <span className={cx(styles.dot, styles[tone])} aria-hidden="true" />
        <span className={styles.outcomeLabel}>{data.title}</span>
      </span>
    </div>
  );
}

export function LaneCard({ data }: NodeProps<LaneNode>) {
  return (
    <div className={styles.lane}>
      <span className={styles.laneTitle}>{data.title}</span>
    </div>
  );
}

export const nodeTypes = { step: StepCard, outcome: OutcomeCard, lane: LaneCard };
