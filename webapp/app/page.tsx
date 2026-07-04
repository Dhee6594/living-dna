"use client";
/** Dashboard — org overview from /api/report + /api/profiles. */
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { api } from "@/lib/api";
import { filterByRepo, usePrefs } from "@/lib/store";
import { ownershipHealth, pct } from "@/lib/format";
import { Badge, Card, Empty, ErrorNote, PageHeader, Skeleton, Stat, rise } from "@/components/ui";
import { RecommendationList, useInsights } from "@/components/insights";
import type { Profile, QualityReport } from "@/lib/types";

export default function Dashboard() {
  const repo = usePrefs((s) => s.repo);
  const { doc: insights } = useInsights();
  const [report, setReport] = useState<QualityReport | null>(null);
  const [profiles, setProfiles] = useState<Profile[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    Promise.all([api.report(), api.profiles()])
      .then(([r, p]) => { setReport(r); setProfiles(p); })
      .catch(setError);
  }, []);

  if (error) return <ErrorNote error={error} />;
  if (!report || !profiles)
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} />)}
      </div>
    );

  const visible = filterByRepo(profiles, repo);
  const risky = visible
    .flatMap((p) => p.risks.map((r) => ({ svc: p.entity, ...r })))
    .sort((a, b) => b.score - a.score);

  return (
    <>
      <PageHeader
        title="Organization genome"
        sub={`${report.commits.toLocaleString()} commits sequenced · ${report.people.humans} humans · ${report.people.bots_filtered} bots filtered`}
      />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Services" value={visible.length} />
        <Stat label="Dependency edges" value={report.dependency_edges} />
        <Stat label="Active risks" value={risky.length} tone={risky.length ? "warn" : "good"} />
        <Stat
          label="Renames tracked"
          value={report.renames_tracked}
        />
      </div>

      {insights && insights.recommendations.length > 0 && (
        <motion.div {...rise} className="mt-6">
          <Card>
            <div className="mb-3 flex items-center gap-2">
              <h2 className="text-sm font-medium text-muted">What to do next</h2>
              <span className="text-xs text-muted/70">
                ranked by impact · risk · confidence · effort
              </span>
            </div>
            <RecommendationList recs={insights.recommendations} limit={3} />
          </Card>
        </motion.div>
      )}

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <motion.div {...rise}>
          <Card>
            <h2 className="mb-3 text-sm font-medium text-muted">Services</h2>
            <ul className="divide-y divide-edge/60">
              {visible.map((p) => (
                <li key={p.id} className="flex items-center gap-3 py-2">
                  <Link
                    href={`/genome?focus=${p.id}`}
                    className="font-medium hover:text-accent"
                  >
                    {p.entity}
                  </Link>
                  <span className="text-xs text-muted">{p.dir}</span>
                  <span className="ml-auto">
                    <Badge tone={ownershipHealth(p.knowledge.effective_owners)}>
                      {p.knowledge.effective_owners} owners
                    </Badge>
                  </span>
                </li>
              ))}
              {visible.length === 0 && <Empty>No services in this repository.</Empty>}
            </ul>
          </Card>
        </motion.div>

        <motion.div {...rise}>
          <Card>
            <h2 className="mb-3 text-sm font-medium text-muted">Top risks</h2>
            {risky.length === 0 && <Empty>No derived risks. Healthy genome.</Empty>}
            <ul className="space-y-2">
              {risky.slice(0, 6).map((r, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <Badge tone={r.score >= 0.7 ? "bad" : "warn"}>{pct(r.score)}</Badge>
                  <div>
                    <span className="font-medium">{r.svc}</span>{" "}
                    <span className="text-muted">{r.note}</span>
                  </div>
                </li>
              ))}
            </ul>
            {report.inspect.length > 0 && (
              <>
                <h3 className="mb-2 mt-4 text-xs uppercase tracking-wide text-muted">
                  Quality flags
                </h3>
                <ul className="space-y-1 text-xs text-muted">
                  {report.inspect.slice(0, 4).map((f, i) => <li key={i}>· {f}</li>)}
                </ul>
              </>
            )}
          </Card>
        </motion.div>
      </div>
    </>
  );
}
