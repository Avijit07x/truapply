import { BaseEdge, type Edge, EdgeLabelRenderer, type EdgeProps } from "@xyflow/react";
import { cx } from "../../lib/cx";
import type { Link } from "./flow";
import styles from "./Workflow.module.css";

type Point = readonly [number, number];

export type FlowEdgeData = {
  kind: Link["kind"];
  label?: string;
  automatic: boolean;
  running: boolean;
  route?: { gapX: number; exitY: number };
};
export type FlowEdge = Edge<FlowEdgeData, "flow">;

const BRANCH_STUB = 18;
const LEVEL = 6;
const START_LABEL_DROP = 16;

function polyline(points: readonly Point[]): string {
  return points
    .map(([x, y], index) => `${index === 0 ? "M" : "L"} ${String(x)} ${String(y)}`)
    .join(" ");
}

function pointsFor(data: FlowEdgeData | undefined, source: Point, target: Point): readonly Point[] {
  const [sx, sy] = source;
  const [tx, ty] = target;
  if (data?.route) {
    const { gapX, exitY } = data.route;
    return [source, [sx, exitY], [gapX, exitY], [gapX, ty], target];
  }
  if (data?.kind === "branch") {
    if (Math.abs(ty - sy) < LEVEL) {
      return [source, [tx, sy]];
    }
    const junction = sx + BRANCH_STUB;
    return [source, [junction, sy], [junction, ty], target];
  }
  return Math.abs(tx - sx) < LEVEL
    ? [source, [sx, ty]]
    : [source, [sx, (sy + ty) / 2], [tx, (sy + ty) / 2], target];
}

function labelAt(data: FlowEdgeData | undefined, source: Point, target: Point): Point {
  if (data?.route) {
    return [source[0], source[1] + START_LABEL_DROP];
  }
  return [(source[0] + target[0]) / 2, (source[1] + target[1]) / 2];
}

export function FlowEdgeLine({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  data,
}: EdgeProps<FlowEdge>) {
  const source: Point = [sourceX, sourceY];
  const target: Point = [targetX, targetY];
  const [labelX, labelY] = labelAt(data, source, target);
  const automatic = data?.automatic ?? false;
  return (
    <>
      <BaseEdge
        id={id}
        path={polyline(pointsFor(data, source, target))}
        className={cx(
          styles.edge,
          automatic && styles.autoEdge,
          automatic && data?.running && styles.liveEdge,
        )}
      />
      {data?.label && (
        <EdgeLabelRenderer>
          <span
            className={styles.edgeLabel}
            style={{
              transform: `translate(-50%, -50%) translate(${String(labelX)}px, ${String(labelY)}px)`,
            }}
          >
            {data.label}
          </span>
        </EdgeLabelRenderer>
      )}
    </>
  );
}

export const edgeTypes = { flow: FlowEdgeLine };
