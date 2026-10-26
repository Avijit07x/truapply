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
import { GROUP_OF, buildEdges, buildNodes, refreshNodes } from "./graph";
import { Inspector } from "./Inspector";
import { type FlowNode, nodeTypes } from "./nodes";
import styles from "./Workflow.module.css";

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
        Your jobs. Click one for details.
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
  const [nodes, setNodes] = useState(() => buildNodes(data.groups, running));
  const [shown, setShown] = useState({ groups: data.groups, running });
  if (shown.groups !== data.groups || shown.running !== running) {
    setShown({ groups: data.groups, running });
    setNodes((current) => refreshNodes(current, data.groups, running));
  }
  const edges = useMemo(() => buildEdges(running), [running]);
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
  const group = selected ? GROUP_OF.get(selected) : undefined;
  return (
    <div className={styles.page}>
      <h1 className={styles.hiddenTitle}>Workflow</h1>
      <div className={styles.canvas} ref={canvas}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          onNodesChange={onNodesChange}
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
        {group && (
          <Inspector
            key={group}
            group={group}
            count={data.groups[group]}
            onClose={clearSelection}
          />
        )}
      </div>
    </div>
  );
}
