"use client";
/** Time Travel — the architecture as of any date, plus a structural diff. */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { GenomeGraph } from "@/components/genome-graph";
import { Badge, Card, ErrorNote, PageHeader, Skeleton } from "@/components/ui";
import type { DiffResult, GraphAt } from "@/lib/types";

export default function TimeTravelPage() {
  const [at, setAt] = useState("");
  const [from, setFrom] = useState("");
  const [graph, setGraph] = useState<GraphAt | null>(null);
  const [diff, setDiff] = useState<DiffResult | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api.graph(at || undefined).then(setGraph).catch(setError);
  }, [at]);

  useEffect(() => {
    if (!from) return setDiff(null);
    api.diff(from, at || undefined).then(setDiff).catch(setError);
  }, [from, at]);

  if (error) return <ErrorNote error={error} />;

  return (
    <>
      <PageHeader
        title="Time travel"
        sub="Bitemporal queries: the graph as the world was, not as we later learned it."
      />
      <div className="mb-4 flex flex-wrap items-end gap-4">
        <label className="text-sm">
          <span className="mb-1 block text-xs text-muted">View architecture at</span>
          <input
            type="date"
            value={at}
            onChange={(e) => setAt(e.target.value)}
            className="rounded-lg border border-edge bg-panel px-3 py-1.5 text-sm"
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-xs text-muted">Diff from</span>
          <input
            type="date"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
            className="rounded-lg border border-edge bg-panel px-3 py-1.5 text-sm"
          />
        </label>
        {(at || from) && (
          <button
            onClick={() => { setAt(""); setFrom(""); }}
            className="rounded-lg border border-edge px-3 py-1.5 text-sm text-muted hover:text-ink"
          >
            Reset to now
          </button>
        )}
      </div>

      {!graph ? <Skeleton className="h-[480px]" /> : <GenomeGraph graph={graph} />}

      {diff && (
        <Card className="mt-4">
          <h2 className="mb-3 text-sm font-medium text-muted">
            What changed · {diff.from} → {diff.to}
          </h2>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <h3 className="mb-1 text-xs uppercase text-muted">Services added</h3>
              <ul className="space-y-1 text-sm">
                {diff.services_added.map((s) => (
                  <li key={s.id}>
                    <Badge tone="good">+</Badge> {s.id.replace("svc:", "")}
                    {s.cause && <span className="ml-1 text-xs text-muted">— “{s.cause}”</span>}
                  </li>
                ))}
                {diff.services_added.length === 0 && <li className="text-muted">none</li>}
              </ul>
              <h3 className="mb-1 mt-3 text-xs uppercase text-muted">Services removed</h3>
              <ul className="space-y-1 text-sm">
                {diff.services_removed.map((s) => (
                  <li key={s}><Badge tone="bad">−</Badge> {s.replace("svc:", "")}</li>
                ))}
                {diff.services_removed.length === 0 && <li className="text-muted">none</li>}
              </ul>
            </div>
            <div>
              <h3 className="mb-1 text-xs uppercase text-muted">Dependencies added</h3>
              <ul className="space-y-1 font-mono text-xs">
                {diff.dependencies_added.map((d) => <li key={d}>+ {d}</li>)}
                {diff.dependencies_added.length === 0 && <li className="text-muted">none</li>}
              </ul>
              <h3 className="mb-1 mt-3 text-xs uppercase text-muted">Dependencies removed</h3>
              <ul className="space-y-1 font-mono text-xs">
                {diff.dependencies_removed.map((d) => <li key={d}>− {d}</li>)}
                {diff.dependencies_removed.length === 0 && <li className="text-muted">none</li>}
              </ul>
            </div>
          </div>
        </Card>
      )}
    </>
  );
}
