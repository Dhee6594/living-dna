"use client";
/** Risk Intelligence — every derived risk with score, class, and evidence. */
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { filterByRepo, usePrefs } from "@/lib/store";
import { pct, riskTone } from "@/lib/format";
import { Badge, Card, Empty, ErrorNote, PageHeader, Skeleton } from "@/components/ui";
import { useInsights } from "@/components/insights";
import type { Profile } from "@/lib/types";

type RiskRow = { svc: string; class: string; score: number; note: string; evidence: string[] };

export default function RiskPage() {
  const repo = usePrefs((s) => s.repo);
  const { doc: insights } = useInsights();
  const [profiles, setProfiles] = useState<Profile[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [klass, setKlass] = useState<string>("");

  useEffect(() => {
    api.profiles().then(setProfiles).catch(setError);
  }, []);

  const rows = useMemo<RiskRow[]>(() => {
    if (!profiles) return [];
    return filterByRepo(profiles, repo)
      .flatMap((p) => p.risks.map((r) => ({ svc: p.entity, ...r })))
      .filter((r) => !klass || r.class === klass)
      .sort((a, b) => b.score - a.score);
  }, [profiles, repo, klass]);

  const classes = useMemo(
    () => [...new Set(rows.map((r) => r.class))],
    [rows],
  );

  if (error) return <ErrorNote error={error} />;

  return (
    <>
      <PageHeader
        title="Risk intelligence"
        sub="Derived from the graph — knowledge concentration, bottlenecks. Backtested predictions arrive with the risk engine phase."
      />
      <div className="mb-4 flex gap-2">
        <button
          onClick={() => setKlass("")}
          aria-pressed={!klass}
          className={`rounded-full border px-3 py-1 text-xs ${!klass ? "border-accent text-accent" : "border-edge text-muted"}`}
        >
          all
        </button>
        {classes.map((c) => (
          <button
            key={c}
            onClick={() => setKlass(c)}
            aria-pressed={klass === c}
            className={`rounded-full border px-3 py-1 text-xs ${klass === c ? "border-accent text-accent" : "border-edge text-muted"}`}
          >
            {c.replace("_", " ")}
          </button>
        ))}
      </div>
      {insights && (
        <div className="mb-6 grid gap-4 md:grid-cols-2">
          <Card>
            <h2 className="mb-2 text-sm font-medium">
              Hidden coupling{" "}
              <span className="font-normal text-muted">— invisible on GitHub</span>
            </h2>
            {insights.architecture.hidden_dependencies.length === 0 ? (
              <p className="text-sm text-muted">None detected.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {insights.architecture.hidden_dependencies.slice(0, 5).map((h, i) => (
                  <li key={i}>
                    <span className="font-medium">{h.a} ↔ {h.b}</span>{" "}
                    <Badge tone="warn">{h.co_changes}× together</Badge>
                    <span className="ml-1 text-xs text-muted">no declared dependency</span>
                  </li>
                ))}
              </ul>
            )}
            {insights.architecture.circular_dependencies.length > 0 && (
              <>
                <h3 className="mb-1 mt-4 text-xs uppercase tracking-wide text-muted">
                  Dependency cycles
                </h3>
                <ul className="space-y-1 font-mono text-xs">
                  {insights.architecture.circular_dependencies.map((c, i) => (
                    <li key={i}><Badge tone="bad">cycle</Badge> {c.join(" → ")}</li>
                  ))}
                </ul>
              </>
            )}
            <p className="mt-3 border-t border-edge/60 pt-2 text-xs text-muted">
              {insights.architecture.boundary_assessment}
            </p>
          </Card>
          <Card>
            <h2 className="mb-2 text-sm font-medium">Single points of failure</h2>
            {insights.risk_intelligence.single_points_of_failure.length === 0 ? (
              <p className="text-sm text-muted">No person is critical to any service.</p>
            ) : (
              <ul className="space-y-1.5 text-sm">
                {insights.risk_intelligence.single_points_of_failure.map((s) => (
                  <li key={s.person_id} className="flex items-center gap-2">
                    <span className="font-medium">{s.person}</span>
                    <Badge tone="bad">{s.critical_services} critical</Badge>
                    <span className="text-xs text-muted">{s.services_impacted} impacted</span>
                  </li>
                ))}
              </ul>
            )}
            {insights.risk_intelligence.scaling_bottlenecks.length > 0 && (
              <>
                <h3 className="mb-1 mt-4 text-xs uppercase tracking-wide text-muted">
                  Scaling bottlenecks
                </h3>
                <ul className="space-y-1 text-sm">
                  {insights.risk_intelligence.scaling_bottlenecks.map((b, i) => (
                    <li key={i}>
                      <span className="font-medium">{b.service}</span>{" "}
                      <span className="text-xs text-muted">
                        {b.dependents} dependents · {b.commits_90d} changes/90d
                      </span>
                    </li>
                  ))}
                </ul>
              </>
            )}
            {insights.risk_intelligence.unowned_services.length > 0 && (
              <p className="mt-3 text-xs text-muted">
                Unowned: {insights.risk_intelligence.unowned_services.join(", ")}
              </p>
            )}
          </Card>
        </div>
      )}

      {!profiles ? (
        <Skeleton className="h-64" />
      ) : rows.length === 0 ? (
        <Empty>No risks derived. That is the good outcome.</Empty>
      ) : (
        <div className="space-y-3">
          {rows.map((r, i) => (
            <Card key={i}>
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={riskTone(r.score)}>{pct(r.score)}</Badge>
                <span className="font-medium">{r.svc}</span>
                <span className="text-xs uppercase tracking-wide text-muted">
                  {r.class.replace("_", " ")}
                </span>
              </div>
              <p className="mt-2 text-sm text-muted">{r.note}</p>
              {r.evidence.length > 0 && (
                <p className="mt-1 font-mono text-xs text-muted/70">⌖ {r.evidence.join(" · ")}</p>
              )}
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
