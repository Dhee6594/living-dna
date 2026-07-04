"use client";
/** Software Genome visualization — dependency graph + service profile drawer. */
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { GenomeGraph } from "@/components/genome-graph";
import { Badge, Card, ErrorNote, PageHeader, Skeleton } from "@/components/ui";
import { ownershipHealth, pct } from "@/lib/format";
import type { GraphAt, Profile } from "@/lib/types";

function GenomePageInner() {
  const focus = useSearchParams().get("focus");
  const [graph, setGraph] = useState<GraphAt | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api.graph().then(setGraph).catch(setError);
  }, []);

  useEffect(() => {
    if (!focus) return setProfile(null);
    api.profile(focus.replace(/^svc:/, "")).then(setProfile).catch(() => setProfile(null));
  }, [focus]);

  if (error) return <ErrorNote error={error} />;

  return (
    <>
      <PageHeader
        title="Software genome"
        sub="Current dependency structure. Every edge carries its since-date and evidence."
      />
      {!graph ? (
        <Skeleton className="h-[520px]" />
      ) : (
        <GenomeGraph graph={graph} focus={focus} />
      )}

      {profile && (
        <Card className="mt-4">
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-lg font-semibold">{profile.entity}</h2>
            <Badge tone={ownershipHealth(profile.knowledge.effective_owners)}>
              {profile.knowledge.effective_owners} effective owners
            </Badge>
            {profile.born && <span className="text-sm text-muted">born {profile.born}</span>}
            <span className="text-sm text-muted">
              {profile.stats.lifetime_commits} lifetime commits
            </span>
          </div>
          {profile.born_msg && (
            <p className="mt-2 text-sm text-muted">
              Origin: <span className="font-mono text-xs">{profile.born_commit?.slice(0, 8)}</span>{" "}
              &ldquo;{profile.born_msg}&rdquo;
            </p>
          )}
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <div>
              <h3 className="mb-2 text-xs uppercase tracking-wide text-muted">Knows it best</h3>
              <ul className="space-y-1 text-sm">
                {profile.knowledge.top.map((o) => (
                  <li key={o.person_id} className="flex justify-between">
                    <span>{o.person}</span>
                    <span className="tabular-nums text-muted">{pct(o.weight)}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="mb-2 text-xs uppercase tracking-wide text-muted">Depends on</h3>
              <ul className="space-y-1 text-sm">
                {profile.dependencies.map((d) => (
                  <li key={d.on}>
                    {d.on} <span className="text-xs text-muted">since {d.since ?? "?"}</span>
                  </li>
                ))}
                {profile.dependencies.length === 0 && <li className="text-muted">none</li>}
              </ul>
            </div>
            <div>
              <h3 className="mb-2 text-xs uppercase tracking-wide text-muted">Risks</h3>
              <ul className="space-y-1 text-sm">
                {profile.risks.map((r, i) => (
                  <li key={i}>
                    <Badge tone={r.score >= 0.7 ? "bad" : "warn"}>{pct(r.score)}</Badge>{" "}
                    <span className="text-muted">{r.note}</span>
                  </li>
                ))}
                {profile.risks.length === 0 && <li className="text-muted">none derived</li>}
              </ul>
            </div>
          </div>
        </Card>
      )}
    </>
  );
}

export default function GenomePage() {
  return (
    <Suspense fallback={<Skeleton className="h-[520px]" />}>
      <GenomePageInner />
    </Suspense>
  );
}
