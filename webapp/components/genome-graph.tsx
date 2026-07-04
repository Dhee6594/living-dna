"use client";
/** Software Genome visualization — React Flow over /api/graph.
 *  Layered left-to-right layout computed from dependency depth (no extra
 *  layout dependency; deterministic and fast for genome-scale graphs). */
import { useEffect, useMemo } from "react";
import {
  Background, Controls, Handle, MiniMap, Position, ReactFlow,
  useEdgesState, useNodesState, type Edge, type Node, type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { GraphAt } from "@/lib/types";

type SvcNode = Node<{ label: string; born: string | null; focus: boolean }, "svc">;

function depthMap(g: GraphAt): Map<string, number> {
  // Longest-path layering: depth(n) = 1 + max(depth of dependencies)
  const deps = new Map<string, string[]>();
  g.dependencies.forEach((e) => {
    deps.set(e.src, [...(deps.get(e.src) ?? []), e.dst]);
  });
  const depth = new Map<string, number>();
  const visiting = new Set<string>();
  const visit = (id: string): number => {
    if (depth.has(id)) return depth.get(id)!;
    if (visiting.has(id)) return 0; // cycle guard
    visiting.add(id);
    const d = Math.max(0, ...(deps.get(id) ?? []).map((t) => visit(t) + 1));
    visiting.delete(id);
    depth.set(id, d);
    return d;
  };
  g.services.forEach((s) => visit(s.id));
  return depth;
}

function SvcNodeView({ data }: NodeProps<SvcNode>) {
  return (
    <div
      className={`rounded-lg border px-3 py-2 text-xs shadow-sm ${
        data.focus
          ? "border-accent bg-accent/15 text-accent"
          : "border-edge bg-panel text-ink"
      }`}
    >
      <Handle type="target" position={Position.Left} className="!bg-edge" />
      <div className="font-medium">{data.label}</div>
      {data.born && <div className="mt-0.5 text-[10px] text-muted">born {data.born}</div>}
      <Handle type="source" position={Position.Right} className="!bg-edge" />
    </div>
  );
}

const nodeTypes = { svc: SvcNodeView };

export function GenomeGraph({ graph, focus }: { graph: GraphAt; focus?: string | null }) {
  const initial = useMemo(() => {
    const depths = depthMap(graph);
    const perCol = new Map<number, number>();
    const nodes: SvcNode[] = graph.services.map((s) => {
      const d = depths.get(s.id) ?? 0;
      const row = perCol.get(d) ?? 0;
      perCol.set(d, row + 1);
      return {
        id: s.id,
        type: "svc",
        position: { x: 40 + d * 240, y: 40 + row * 110 },
        data: { label: s.name, born: s.born, focus: s.id === focus },
      };
    });
    const edges: Edge[] = graph.dependencies.map((e) => ({
      id: `${e.src}->${e.dst}`,
      source: e.src,
      target: e.dst,
      animated: true,
      label: e.since ? `since ${e.since}` : undefined,
      labelStyle: { fontSize: 10, fill: "rgb(var(--muted))" },
      style: { stroke: "rgb(var(--edge))" },
    }));
    return { nodes, edges };
  }, [graph, focus]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initial.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initial.edges);

  useEffect(() => {
    setNodes(initial.nodes);
    setEdges(initial.edges);
  }, [initial, setNodes, setEdges]);

  return (
    <div className="h-[520px] rounded-xl border border-edge bg-panel" role="figure" aria-label="Service dependency graph">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={24} color="rgb(var(--edge))" />
        <MiniMap pannable className="!bg-panel" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
