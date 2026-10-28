import { useQuery, useSuspenseQuery } from "@tanstack/react-query";
import {
  Background,
  BackgroundVariant,
  type NodeChange,
  Panel,
  ReactFlow,
  applyNodeChanges,
} from "@xyflow/react";
import "@xyflow/react/dist/base.css";
import { useCallback, useMemo, useRef, useState } from "react";
import { queries } from "../../api/queries";
import { CanvasControls } from "./CanvasControls";
import { edgeTypes } from "./FlowEdge";
import { buildEdges, buildNodes, pathThrough, refreshNodes } from "./graph";
import { Inspector } from "./Inspector";
import { type FlowNode, nodeTypes } from "./nodes";
import styles from "./Workflow.module.css";

const LIVE_MS = 1_500;

function Legend({ running }: { running: boolean }) {
  return (
    <Panel position="bottom-center" className={styles.legend} aria-label="How to read the map">
      <span className={styles.legendItem}>
        <span className={styles.legendQuestion} aria-hidden="true">
          ?
        </span>
        Question with branches
      </span>
      <span className={styles.legendItem}>
        <span className={styles.legendAuto} aria-hidden="true" />
        Done for you automatically
      </span>
      <span className={styles.legendItem}>
        <span className={styles.legendJobs} aria-hidden="true">
          3
        </span>
        Click any box to change its settings or run it.
      </span>
      {running && (
        <span className={styles.legendLive}>
          <span className={styles.livePip} aria-hidden="true" />
          Live: a run is going
        </span>
      )}
    </Panel>
  );
}

export default function WorkflowPage() {
  const { data } = useSuspenseQuery(queries.workflow());
  const running = useQuery(queries.summary()).data?.run.running ?? false;
  const run = useQuery({ ...queries.runs(), refetchInterval: running ? LIVE_MS : false }).data;
  const stage = run?.running ? run.stage : null;
  const added = data.lastRun?.groups ?? null;
  const live = { running, stage, added };
  const [nodes, setNodes] = useState(() => buildNodes(data.groups, live));
  const [shown, setShown] = useState({ groups: data.groups, running, stage });
  if (shown.groups !== data.groups || shown.running !== running || shown.stage !== stage) {
    setShown({ groups: data.groups, running, stage });
    setNodes((current) => refreshNodes(current, data.groups, live));
  }
  const [hovered, setHovered] = useState<string | null>(null);
  const path = useMemo(() => (hovered ? pathThrough(hovered) : null), [hovered]);
  const edges = useMemo(() => {
    const built = buildEdges(data.groups, running);
    if (!path) {
      return built;
    }
    return built.map((edge) =>
      edge.data ? { ...edge, data: { ...edge.data, dim: !path.edges.has(edge.id) } } : edge,
    );
  }, [data.groups, running, path]);
  const shownNodes = useMemo(() => {
    if (!path) {
      return nodes;
    }
    return nodes.map((node) =>
      node.type === "lane" || path.nodes.has(node.id)
        ? node
        : { ...node, className: styles.dimNode },
    );
  }, [nodes, path]);
  const onNodesChange = useCallback((changes: NodeChange<FlowNode>[]) => {
    setNodes((current) => applyNodeChanges(changes, current));
  }, []);
  const clearSelection = useCallback(() => {
    setNodes((current) =>
      current.map((node) => (node.selected ? { ...node, selected: false } : node)),
    );
  }, []);
  const canvas = useRef<HTMLDivElement>(null);
  const selected = nodes.find((node) => node.selected)?.id ?? null;
  return (
    <div className={styles.page}>
      <h1 className={styles.hiddenTitle}>Workflow</h1>
      <div className={styles.canvas} ref={canvas}>
        <ReactFlow
          nodes={shownNodes}
          edges={edges}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          onNodesChange={onNodesChange}
          onNodeMouseEnter={(_event, node) => {
            setHovered(node.type === "lane" ? null : node.id);
          }}
          onNodeMouseLeave={() => {
            setHovered(null);
          }}
          minZoom={0.3}
          maxZoom={1.75}
          nodesDraggable={false}
          nodesConnectable={false}
          edgesFocusable={false}
          zoomOnDoubleClick={false}
          aria-label="Workflow map"
        >
          <Background variant={BackgroundVariant.Dots} gap={18} size={1} className={styles.dots} />
          <CanvasControls container={canvas} />
          <Legend running={running} />
        </ReactFlow>
        {selected && (
          <Inspector
            key={selected}
            node={selected}
            counts={data.groups}
            lastRun={data.lastRun}
            run={run}
            onClose={clearSelection}
          />
        )}
      </div>
    </div>
  );
}
