"use client";
/** Bus Factor — org heatmap + departure simulation with succession plans. */
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { pct } from "@/lib/format";
import { Badge, Card, Empty, ErrorNote, PageHeader, Skeleton } from "@/components/ui";
import type { BusFactorSim, OrgBusFactorRow } from "@/lib/types";

function BusFactorInner() {
  const preselect = useSearchParams().get("person");
  const [org, setOrg] = useState<OrgBusFactorRow[] | null>(null);
  const [sim, setSim] = useState<BusFactorSim | null>(null);
  const [who, setWho] = useState<string | null>(preselect);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api.busfactorOrg().then(setOrg).catch(setError);
  }, []);

  useEffect(() => {
    if (!who) return setSim(null);
    api.busfactorPerson(who).then(setSim).catch(setError);
  }, [who]);

  if (error) return <ErrorNote error={error} />;

  return (
    <>
      <PageHeader
        title="Bus factor"
        sub="Departure simulations over KNOWS edges. Click a person to run the what-if."
      />
      <div className="grid gap-4 lg:grid-cols-5">
        <Card className="lg:col-span-2">
          <h2 className="mb-3 text-sm font-medium text-muted">Org heatmap</h2>
          {!org ? (
            <Skeleton className="h-48" />
          ) : (
            <ul className="divide-y divide-edge/60" role="list">
              {org.map((r) => (
                <li key={r.person_id}>
                  <button
                    onClick={() => setWho(r.person)}
                    aria-pressed={who === r.person}
                    className={`flex w-full items-center gap-2 px-1 py-2 text-left text-sm hover:bg-edge/30 ${
                      who === r.person ? "text-accent" : ""
                    }`}
                  >
                    <span className="flex-1 truncate">{r.person}</span>
                    {r.critical_services > 0 && (
                      <Badge tone="bad">{r.critical_services} critical</Badge>
                    )}
                    <span className="text-xs tabular-nums text-muted">
                      {r.services_impacted} impacted
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <div className="lg:col-span-3">
          {!sim ? (
            <Empty>Select a person to simulate their departure.</Empty>
          ) : (
            <Card>
              <h2 className="text-sm font-medium">
                If <span className="text-accent">{sim.person}</span> leaves…
              </h2>
              <p className="mt-1 text-sm text-muted">
                {sim.services_impacted} services impacted · {sim.critical.length} critical
              </p>
              <ul className="mt-4 space-y-3">
                {sim.details.map((d) => (
                  <li key={d.service} className="rounded-lg border border-edge/60 p-3">
                    <div className="flex flex-wrap items-center gap-2 text-sm">
                      <span className="font-medium">{d.service}</span>
                      {d.critical && <Badge tone="bad">critical</Badge>}
                      <span className="ml-auto text-xs text-muted">
                        loses {pct(d.knowledge_lost)} · ~{d.recovery_estimate_weeks} wks recovery
                      </span>
                    </div>
                    <div
                      className="mt-2 h-2 overflow-hidden rounded-full bg-edge/50"
                      role="img"
                      aria-label={`${pct(d.knowledge_lost)} knowledge lost`}
                    >
                      <div className="h-full bg-bad/70" style={{ width: pct(d.knowledge_lost) }} />
                    </div>
                    {d.succession.length > 0 && (
                      <p className="mt-2 text-xs text-muted">
                        Succession: pair with{" "}
                        {d.succession
                          .map((s) => `${s.pair_with} (${pct(s.current_weight)})`)
                          .join(", ")}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}

export default function BusFactorPage() {
  return (
    <Suspense fallback={<Skeleton className="h-64" />}>
      <BusFactorInner />
    </Suspense>
  );
}
