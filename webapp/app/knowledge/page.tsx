"use client";
/** Knowledge Graph explorer — who knows what, across the org. */
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { filterByRepo, usePrefs } from "@/lib/store";
import { ownershipHealth, pct } from "@/lib/format";
import { Badge, Card, Empty, ErrorNote, PageHeader, Skeleton } from "@/components/ui";
import type { Profile } from "@/lib/types";

export default function KnowledgePage() {
  const repo = usePrefs((s) => s.repo);
  const [profiles, setProfiles] = useState<Profile[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [personFilter, setPersonFilter] = useState("");

  useEffect(() => {
    api.profiles().then(setProfiles).catch(setError);
  }, []);

  const rows = useMemo(() => {
    if (!profiles) return [];
    const visible = filterByRepo(profiles, repo);
    const byPerson = new Map<string, { service: string; weight: number; eff: number }[]>();
    visible.forEach((p) =>
      p.knowledge.top.forEach((o) => {
        byPerson.set(o.person, [
          ...(byPerson.get(o.person) ?? []),
          { service: p.entity, weight: o.weight, eff: p.knowledge.effective_owners },
        ]);
      }),
    );
    return [...byPerson.entries()]
      .filter(([name]) => name.toLowerCase().includes(personFilter.toLowerCase()))
      .map(([name, svcs]) => ({
        name,
        svcs: svcs.sort((a, b) => b.weight - a.weight),
        total: svcs.reduce((s, x) => s + x.weight, 0),
      }))
      .sort((a, b) => b.total - a.total);
  }, [profiles, repo, personFilter]);

  if (error) return <ErrorNote error={error} />;

  return (
    <>
      <PageHeader
        title="Knowledge graph"
        sub="KNOWS edges derived from git history with 12-month half-life decay, normalized per service."
      />
      <input
        value={personFilter}
        onChange={(e) => setPersonFilter(e.target.value)}
        placeholder="Filter people…"
        aria-label="Filter people"
        className="mb-4 w-full max-w-xs rounded-lg border border-edge bg-panel px-3 py-1.5 text-sm"
      />
      {!profiles ? (
        <Skeleton className="h-64" />
      ) : rows.length === 0 ? (
        <Empty>No knowledge edges match.</Empty>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {rows.map((r) => (
            <Card key={r.name}>
              <h2 className="mb-2 font-medium">{r.name}</h2>
              <ul className="space-y-1.5">
                {r.svcs.map((s) => (
                  <li key={s.service} className="flex items-center gap-2 text-sm">
                    <span className="w-32 truncate">{s.service}</span>
                    <div
                      className="h-2 flex-1 overflow-hidden rounded-full bg-edge/50"
                      role="img"
                      aria-label={`${pct(s.weight)} of ${s.service} knowledge`}
                    >
                      <div
                        className="h-full rounded-full bg-accent"
                        style={{ width: pct(s.weight) }}
                      />
                    </div>
                    <span className="w-12 text-right text-xs tabular-nums text-muted">
                      {pct(s.weight)}
                    </span>
                    <Badge tone={ownershipHealth(s.eff)}>{s.eff}</Badge>
                  </li>
                ))}
              </ul>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
