import type { Group } from "../../api/types";
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

export function buildNodes(counts: Counts, running: boolean): FlowNode[] {
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
    data: { step, count: step.group ? counts[step.group] : null, running },
    style: { width: STEP_WIDTH },
    selectable: step.group !== undefined,
    focusable: step.group !== undefined,
  }));
  const outcomes: OutcomeNode[] = OUTCOMES.map((item) => ({
    id: item.id,
    type: "outcome",
    position: { x: item.x, y: item.y },
    data: { group: item.group, branch: item.branch, title: item.title, count: counts[item.group] },
    style: { width: OUTCOME_WIDTH },
  }));
  return [...lanes, ...steps, ...outcomes];
}

export function refreshNodes(nodes: FlowNode[], counts: Counts, running: boolean): FlowNode[] {
  return nodes.map((node) => {
    if (node.type === "step") {
      const { group } = node.data.step;
      return { ...node, data: { ...node.data, count: group ? counts[group] : null, running } };
    }
    if (node.type === "outcome") {
      return { ...node, data: { ...node.data, count: counts[node.data.group] } };
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

export function buildEdges(running: boolean): FlowEdge[] {
  return LINKS.map((link) => {
    const [sourceHandle, targetHandle] = HANDLES[link.kind];
    const route = routeOf(link);
    return {
      id: `${link.from}-${link.to}`,
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
        ...(link.label === undefined ? {} : { label: link.label }),
        ...(route === undefined ? {} : { route }),
      },
    };
  });
}
