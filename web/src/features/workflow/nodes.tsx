import { Handle, type Node, type NodeProps, Position } from "@xyflow/react";
import type { ComponentType } from "react";
import type { Group } from "../../api/types";
import { GROUP_TONE } from "../../domain/groups";
import { cx } from "../../lib/cx";
import { Check, type IconProps, Rows, Spark } from "../../ui/icons";
import type { Step, StepKind } from "./flow";
import styles from "./Workflow.module.css";

export type StepData = { step: Step; count: number | null; running: boolean };
export type OutcomeData = { group: Group; branch: string; title: string; count: number };
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

export function StepCard({ data, selected }: NodeProps<StepNode>) {
  const { step, count, running } = data;
  const live = running && step.kind === "auto";
  return (
    <div
      className={cx(
        styles.card,
        styles[step.kind],
        step.group && styles.clickable,
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
            {count.toLocaleString()}
            {step.countLabel && <small>{step.countLabel}</small>}
          </span>
        )}
      </div>
      <p className={styles.cardTitle}>{step.title}</p>
      {step.note && <p className={styles.cardNote}>{step.note}</p>}
    </div>
  );
}

export function OutcomeCard({ data, selected }: NodeProps<OutcomeNode>) {
  const tone = GROUP_TONE[data.group] ?? "plain";
  return (
    <div className={cx(styles.outcome, styles.clickable, selected && styles.selected)}>
      <Pins sides={["left"]} />
      <span className={styles.outcomeHead}>
        <span className={styles.branch}>{data.branch}</span>
        <span className={cx(styles.outcomeCount, data.count === 0 && styles.zero)}>
          {data.count.toLocaleString()}
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
