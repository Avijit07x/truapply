import { Panel, useNodesInitialized, useReactFlow, useStore } from "@xyflow/react";
import { type RefObject, useEffect, useState } from "react";
import { IconButton } from "../../ui/Button";
import { Collapse, Expand, Frame, Minus, Plus } from "../../ui/icons";
import styles from "./Workflow.module.css";

export const FIT = { padding: 0.04, maxZoom: 1 } as const;

function useFullScreen(target: RefObject<HTMLElement | null>) {
  const [full, setFull] = useState(() => document.fullscreenElement !== null);
  useEffect(() => {
    const update = () => {
      setFull(document.fullscreenElement !== null);
    };
    document.addEventListener("fullscreenchange", update);
    return () => {
      document.removeEventListener("fullscreenchange", update);
    };
  }, []);
  const toggle = () => {
    if (document.fullscreenElement) {
      void document.exitFullscreen();
    } else {
      void target.current?.requestFullscreen();
    }
  };
  return [full, toggle] as const;
}

export function CanvasControls({ container }: { container: RefObject<HTMLElement | null> }) {
  const { zoomIn, zoomOut, fitView } = useReactFlow();
  const measured = useNodesInitialized();
  const width = useStore((state) => state.width);
  const height = useStore((state) => state.height);
  const [full, toggleFull] = useFullScreen(container);
  useEffect(() => {
    if (measured && width > 0 && height > 0) {
      void fitView(FIT);
    }
  }, [measured, width, height, fitView]);
  return (
    <Panel position="bottom-left" className={styles.controls}>
      <IconButton label="Zoom in" onClick={() => void zoomIn()}>
        <Plus size={12} />
      </IconButton>
      <IconButton label="Zoom out" onClick={() => void zoomOut()}>
        <Minus size={12} />
      </IconButton>
      <IconButton label="Fit to screen" onClick={() => void fitView(FIT)}>
        <Frame size={12} />
      </IconButton>
      {document.fullscreenEnabled && (
        <IconButton label={full ? "Leave full screen" : "Full screen"} onClick={toggleFull}>
          {full ? <Collapse size={12} /> : <Expand size={12} />}
        </IconButton>
      )}
    </Panel>
  );
}
