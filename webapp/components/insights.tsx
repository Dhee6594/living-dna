"use client";
/** Shared Insight Engine widgets, reused across Dashboard/Risk/Executive. */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { pct } from "@/lib/format";
import { Badge, Card } from "@/components/ui";
import type { InsightsDoc, Recommendation } from "@/lib/types";

/** Fetch-once hook for the insights document. */
export function useInsights() {
  const [doc, setDoc] = useState<InsightsDoc | null>(null);
  const [error, setError] = useState<unknown>(null);
  useEffect(() => {
    api.insights().then(setDoc).catch(setError);
  }, []);
  return { doc, error };
}

const EFFORT_LABEL = { S: "days", M: "weeks", L: "quarter" } as const;

export function RecommendationList({
  recs,
  limit,
}: {
  recs: Recommendation[];
  limit?: number;
}) {
  const shown = limit ? recs.slice(0, limit) : recs;
  if (shown.length === 0)
    return <p className="text-sm text-muted">No actions recommended — healthy genome.</p>;
  return (
    <ol className="space-y-3">
      {shown.map((r, i) => (
        <li key={i} className="rounded-lg border border-edge/60 p-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold text-muted">#{i + 1}</span>
            <span className="text-sm font-medium">{r.action}</span>
          </div>
          <p className="mt-1 text-xs leading-relaxed text-muted">{r.why}</p>
          <div className="mt-2 flex flex-wrap gap-1.5 text-xs" aria-label="Ranking factors">
            <Badge tone={r.impact >= 4 ? "bad" : "warn"}>impact {r.impact}/5</Badge>
            <Badge tone="muted">risk {r.risk}/5</Badge>
            <Badge tone="muted">confidence {pct(r.confidence)}</Badge>
            <Badge tone="muted">effort {EFFORT_LABEL[r.effort]}</Badge>
          </div>
        </li>
      ))}
    </ol>
  );
}

export function ScoreRing({ label, value }: { label: string; value: number }) {
  const tone = value >= 70 ? "text-good" : value >= 40 ? "text-warn" : "text-bad";
  return (
    <Card className="text-center">
      <div
        className={`text-3xl font-semibold tabular-nums ${label === "Complexity" ? (value >= 70 ? "text-bad" : value >= 40 ? "text-warn" : "text-good") : tone}`}
        aria-label={`${label} ${value} out of 100`}
      >
        {value}
      </div>
      <div className="mt-1 text-xs uppercase tracking-wide text-muted">{label}</div>
    </Card>
  );
}
