import { BaseEdge, type Edge, EdgeLabelRenderer, type EdgeProps } from "@xyflow/react";
import { cx } from "../../lib/cx";
import { prefersLessMotion } from "../../lib/motion";
import type { Link } from "./flow";
import styles from "./Workflow.module.css";

type Point = readonly [number, number];

export type FlowEdgeData = {
  kind: Link["kind"];
  label?: string;
  automatic: boolean;
  running: boolean;
  flowing: boolean;
  dim?: boolean;
  route?: { gapX: number; exitY: number };
};
export type FlowEdge = Edge<FlowEdgeData, "flow">;

const BRANCH_STUB = 18;
const LEVEL = 6;
const START_LABEL_DROP = 16;
const CORNER = 10;
const PIXELS_PER_SECOND = 70;
const SHORTEST_TRIP_S = 1.6;

function pointsFor(data: FlowEdgeData | undefined, source: Point, target: Point): Point[] {
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

function toward(from: Point, to: Point, distance: number): Point {
  const length = Math.hypot(to[0] - from[0], to[1] - from[1]) || 1;
  return [
    from[0] + ((to[0] - from[0]) / length) * distance,
    from[1] + ((to[1] - from[1]) / length) * distance,
  ];
}

function rounded(points: readonly Point[]): string {
  const at = ([x, y]: Point) => `${String(x)} ${String(y)}`;
  const [first, ...rest] = points;
  if (!first) {
    return "";
  }
  let path = `M ${at(first)}`;
  rest.forEach((corner, index) => {
    const previous = points[index] ?? first;
    const next = rest[index + 1];
    if (!next) {
      path += ` L ${at(corner)}`;
      return;
    }
    const inLength = Math.hypot(corner[0] - previous[0], corner[1] - previous[1]);
    const outLength = Math.hypot(next[0] - corner[0], next[1] - corner[1]);
    const radius = Math.min(CORNER, inLength / 2, outLength / 2);
    path += ` L ${at(toward(corner, previous, radius))} Q ${at(corner)} ${at(toward(corner, next, radius))}`;
  });
  return path;
}

function length(points: readonly Point[]): number {
  return points.reduce((total, point, index) => {
    const previous = points[index - 1];
    return previous ? total + Math.hypot(point[0] - previous[0], point[1] - previous[1]) : total;
  }, 0);
}

function labelAt(data: FlowEdgeData | undefined, source: Point, target: Point): Point {
  if (data?.route) {
    return [source[0], source[1] + START_LABEL_DROP];
  }
  return [(source[0] + target[0]) / 2, (source[1] + target[1]) / 2];
}

function Dots({ path, seconds, automatic }: { path: string; seconds: number; automatic: boolean }) {
  return [0, seconds / 2].map((offset) => (
    <circle key={offset} r={2.5} className={cx(styles.particle, automatic && styles.autoParticle)}>
      <animateMotion
        dur={`${String(seconds)}s`}
        begin={`-${String(offset)}s`}
        repeatCount="indefinite"
        path={path}
      />
    </circle>
  ));
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
  const points = pointsFor(data, source, target);
  const path = rounded(points);
  const [labelX, labelY] = labelAt(data, source, target);
  const automatic = data?.automatic ?? false;
  const flowing = data?.flowing ?? false;
  const dim = data?.dim ?? false;
  const seconds = Math.max(SHORTEST_TRIP_S, length(points) / PIXELS_PER_SECOND);
  return (
    <>
      <BaseEdge
        id={id}
        path={path}
        className={cx(
          styles.edge,
          !flowing && styles.idleEdge,
          automatic && styles.autoEdge,
          automatic && data?.running && styles.liveEdge,
          dim && styles.dimEdge,
        )}
      />
      {flowing && !dim && !prefersLessMotion() && (
        <Dots path={path} seconds={seconds} automatic={automatic} />
      )}
      {data?.label && (
        <EdgeLabelRenderer>
          <span
            className={cx(styles.edgeLabel, dim && styles.dimLabel)}
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
