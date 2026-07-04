"use client";
/** Executive dashboard — board-level KPIs computed from existing endpoints. */
import { useEffect, useState } from "react";
import { api, executiveSummary } from "@/lib/api";
import { filterByRepo, usePrefs } from "@/lib/store";
import { Card, ErrorNote, PageHeader, Skeleton, Stat } from "@/components/ui";
import { RecommendationList, ScoreRing, useInsights } from "@/components/insights";
import type { OrgBusFactorRow, Profile, QualityReport } from "@/lib/types";

const AUDIENCES = [
  ["cto", "CTO"],
  ["engineering_manager", "Eng Manager"],
  ["staff_engineer", "Staff Engineer"],
  ["platform_team", "Platform Team"],
] as const;

export default function ExecutivePage() {
  const repo = usePrefs((s) => s.repo);
  const { doc: insights } = useInsights();
  const [audience, setAudience] = useState<(typeof AUDIENCES)[number][0]>("cto");
  const [data, setData] = useState<{
    profiles: Profile[]; org: OrgBusFactorRow[]; report: QualityReport;
  } | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    Promise.all([api.profiles(), api.busfactorOrg(), api.report()])
      .then(([profiles, org, report]) => setData({ profiles, org, report }))
      .catch(setError);
  }, []);

  if (error) return <ErrorNote error={error} />;
  if (!data)
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} />)}
      </div>
    );

  const visible = filterByRepo(data.profiles, repo);
  const s = executiveSummary(visible, data.org);

  return (
    <>
      <PageHeader
        title="Executive view"
        sub="The three questions: who knows it, what breaks, why it was built — as portfolio numbers."
      />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Stat label="Services sequenced" value={s.services} />
        <Stat
          label="Avg effective owners"
          value={s.avgEffectiveOwners}
          tone={s.avgEffectiveOwners >= 2 ? "good" : s.avgEffectiveOwners >= 1.6 ? "warn" : "bad"}
        />
        <Stat
          label="Single-owner services"
          value={s.singleOwnerServices}
          tone={s.singleOwnerServices > 0 ? "bad" : "good"}
        />
        <Stat label="Open risks" value={s.risks} tone={s.risks ? "warn" : "good"} />
        <Stat label="Critical risks" value={s.criticalRisks} tone={s.criticalRisks ? "bad" : "good"} />
        <Stat
          label="Highest departure exposure"
          value={s.highestBusRisk ? s.highestBusRisk.person : "—"}
          tone={s.highestBusRisk && s.highestBusRisk.critical_services > 0 ? "bad" : "good"}
        />
      </div>

      {insights && (
        <>
          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            <ScoreRing label="Maturity" value={insights.overview.maturity_score} />
            <ScoreRing label="Complexity" value={insights.overview.complexity_score} />
            <ScoreRing label="Maintainability" value={insights.overview.maintainability_score} />
          </div>

          <Card className="mt-6">
            <div role="tablist" aria-label="Report audience" className="mb-3 flex flex-wrap gap-2">
              {AUDIENCES.map(([key, label]) => (
                <button
                  key={key}
                  role="tab"
                  aria-selected={audience === key}
                  onClick={() => setAudience(key)}
                  className={`rounded-full border px-3 py-1 text-xs ${
                    audience === key ? "border-accent text-accent" : "border-edge text-muted"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            <p role="tabpanel" className="text-sm leading-relaxed">
              {insights.executive[audience]}
            </p>
            <p className="mt-3 border-t border-edge/60 pt-2 text-xs text-muted">
              Score formulas: {Object.values(insights.overview.score_formulas).join(" · ")} —
              every number is recomputable from the genome; nothing is a black box.
            </p>
          </Card>

          <Card className="mt-6">
            <h2 className="mb-3 text-sm font-medium text-muted">Ranked actions</h2>
            <RecommendationList recs={insights.recommendations} limit={5} />
          </Card>
        </>
      )}

      <Card className="mt-6">
        <h2 className="mb-2 text-sm font-medium text-muted">Reading this page</h2>
        <p className="text-sm leading-relaxed text-muted">
          Effective owners is the exponential of the entropy of each service&apos;s
          contribution distribution — &ldquo;how many people <em>really</em> know
          this.&rdquo; Below 1.6 the genome flags knowledge concentration; one senior
          departure there typically costs $300–500k loaded. Every number above links
          back to evidence — commits, edges, provenance — never to vibes.
        </p>
      </Card>
    </>
  );
}
