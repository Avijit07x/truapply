import type { Group, RunStage } from "../../api/types";
import type { FlowEdge } from "./FlowEdge";
import {
  LANES,
  LANE_WIDTH,
  LINKS,
  type Link,
  OUTCOMES,
  OUTCOME_WIDTH,
  STEPS,
  STEP_WIDTH,
} from "./flow";
import type { FlowNode, LaneNode, OutcomeNode, StepNode } from "./nodes";

type Counts = Record<Group, number>;
export type Live = { running: boolean; stage: RunStage | null; added: Counts | null };

function addedTo(live: Live, group: Group | undefined): number {
  return group && live.added ? live.added[group] : 0;
}

function stepData(step: StepNode["data"]["step"], counts: Counts, live: Live) {
  return {
    step,
    count: step.group ? counts[step.group] : null,
    total: counts.found,
    running: live.running,
    active: live.running && step.stage !== undefined && step.stage === live.stage,
    added: addedTo(live, step.group),
  };
}

const GAP_INSET = 28;
const HANDLES: Record<Link["kind"], readonly [string, string]> = {
  spine: ["bottom", "top"],
  branch: ["right", "left"],
  lane: ["bottom", "left"],
};
const STEP_BY_ID = new Map(STEPS.map((step) => [step.id, step]));

export const GROUP_OF: ReadonlyMap<string, Group> = new Map([
  ...STEPS.flatMap((step) => (step.group ? [[step.id, step.group] as const] : [])),
  ...OUTCOMES.map((item) => [item.id, item.group] as const),
]);

export function buildNodes(counts: Counts, live: Live): FlowNode[] {
  const lanes: LaneNode[] = LANES.map((lane) => ({
    id: lane.id,
    type: "lane",
    position: { x: lane.x, y: 0 },
    data: { title: lane.title },
    style: { width: LANE_WIDTH, height: lane.height },
    selectable: false,
    focusable: false,
  }));
  const steps: StepNode[] = STEPS.map((step) => ({
    id: step.id,
    type: "step",
    position: { x: step.x, y: step.y },
    data: stepData(step, counts, live),
    style: { width: STEP_WIDTH },
  }));
  const outcomes: OutcomeNode[] = OUTCOMES.map((item) => ({
    id: item.id,
    type: "outcome",
    position: { x: item.x, y: item.y },
    data: {
      group: item.group,
      branch: item.branch,
      title: item.title,
      count: counts[item.group],
      total: counts.found,
      added: addedTo(live, item.group),
    },
    style: { width: OUTCOME_WIDTH },
  }));
  return [...lanes, ...steps, ...outcomes];
}

export function refreshNodes(nodes: FlowNode[], counts: Counts, live: Live): FlowNode[] {
  return nodes.map((node) => {
    if (node.type === "step") {
      return { ...node, data: stepData(node.data.step, counts, live) };
    }
    if (node.type === "outcome") {
      const { group } = node.data;
      const count = counts[group];
      const added = addedTo(live, group);
      return { ...node, data: { ...node.data, count, total: counts.found, added } };
    }
    return node;
  });
}

function routeOf(link: Link): { gapX: number; exitY: number } | undefined {
  const source = STEP_BY_ID.get(link.from);
  const target = STEP_BY_ID.get(link.to);
  const lane = source && LANES.find((item) => source.x >= item.x && source.x < item.x + LANE_WIDTH);
  if (link.kind !== "lane" || !target || lane?.exitY === undefined) {
    return undefined;
  }
  return { gapX: target.x - GAP_INSET, exitY: lane.exitY };
}

function linked(direction: "from" | "to"): ReadonlyMap<string, readonly string[]> {
  const found = new Map<string, string[]>();
  for (const link of LINKS) {
    const start = direction === "from" ? link.from : link.to;
    const end = direction === "from" ? link.to : link.from;
    found.set(start, [...(found.get(start) ?? []), end]);
  }
  return found;
}

const NEXT = linked("from");
const PREVIOUS = linked("to");

function reach(start: string, steps: ReadonlyMap<string, readonly string[]>): Set<string> {
  const seen = new Set([start]);
  const waiting = [start];
  for (let id = waiting.pop(); id !== undefined; id = waiting.pop()) {
    for (const next of steps.get(id) ?? []) {
      if (!seen.has(next)) {
        seen.add(next);
        waiting.push(next);
      }
    }
  }
  return seen;
}

export type Path = { nodes: ReadonlySet<string>; edges: ReadonlySet<string> };

export function pathThrough(id: string): Path {
  const before = reach(id, PREVIOUS);
  const after = reach(id, NEXT);
  const edges = LINKS.filter(
    (link) =>
      (before.has(link.from) && before.has(link.to)) ||
      (after.has(link.from) && after.has(link.to)),
  ).map(edgeId);
  return { nodes: new Set([...before, ...after]), edges: new Set(edges) };
}

function carried(counts: Counts): (id: string) => number {
  const known = new Map<string, number>();
  const total = (id: string): number => {
    const cached = known.get(id);
    if (cached !== undefined) {
      return cached;
    }
    const group = GROUP_OF.get(id);
    const own = group && group !== "found" ? counts[group] : 0;
    const sum = (NEXT.get(id) ?? []).reduce((all, next) => all + total(next), own);
    known.set(id, sum);
    return sum;
  };
  return total;
}

function edgeId(link: Link): string {
  return `${link.from}-${link.to}`;
}

export function buildEdges(counts: Counts, running: boolean): FlowEdge[] {
  const total = carried(counts);
  return LINKS.map((link) => {
    const [sourceHandle, targetHandle] = HANDLES[link.kind];
    const route = routeOf(link);
    return {
      id: edgeId(link),
      source: link.from,
      target: link.to,
      sourceHandle,
      targetHandle,
      type: "flow",
      selectable: false,
      focusable: false,
      data: {
        kind: link.kind,
        automatic: link.automatic === true || STEP_BY_ID.get(link.to)?.kind === "auto",
        running,
        flowing: total(link.to) > 0,
        ...(link.label === undefined ? {} : { label: link.label }),
        ...(route === undefined ? {} : { route }),
      },
    };
  });
}
