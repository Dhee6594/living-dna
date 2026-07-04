/** Thin typed client over the existing Python genome API.
 *  All calls go through Next rewrites (/api/* -> DNA_API_URL). */
import type {
  AskAnswer, BusFactorSim, DiffResult, GenomeEvent, GraphAt, InsightsDoc,
  OrgBusFactorRow, Person, Profile, QualityReport, SearchHit,
} from "./types";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function get<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { ...init, headers: { Accept: "application/json" } });
  if (!res.ok) throw new ApiError(res.status, `${path} -> ${res.status}`);
  return (await res.json()) as T;
}

export const api = {
  profiles: () => get<Profile[]>("/api/profiles"),
  profile: (service: string) => get<Profile>(`/api/profile/${encodeURIComponent(service)}`),
  graph: (at?: string) => get<GraphAt>(`/api/graph${at ? `?at=${at}` : ""}`),
  diff: (from: string, to?: string) =>
    get<DiffResult>(`/api/diff?from=${from}&to=${to ?? "now"}`),
  busfactorOrg: () => get<OrgBusFactorRow[]>("/api/busfactor"),
  busfactorPerson: (person: string) =>
    get<BusFactorSim>(`/api/busfactor?person=${encodeURIComponent(person)}`),
  ask: (q: string) => get<AskAnswer>(`/api/ask?q=${encodeURIComponent(q)}`),
  people: () => get<Person[]>("/api/people"),
  report: () => get<QualityReport>("/api/report"),
  insights: () => get<InsightsDoc>("/api/insights"),
  search: (q: string) => get<SearchHit[]>(`/api/search?q=${encodeURIComponent(q)}`),
  events: (opts: { service?: string; limit?: number } = {}) => {
    const p = new URLSearchParams();
    if (opts.service) p.set("service", opts.service);
    if (opts.limit) p.set("limit", String(opts.limit));
    return get<GenomeEvent[]>(`/api/events?${p.toString()}`);
  },
};

/** Aggregate executive metrics client-side from existing endpoints —
 *  deliberately NOT a new backend route (no duplicated logic). */
export function executiveSummary(profiles: Profile[], org: OrgBusFactorRow[]) {
  const risks = profiles.flatMap((p) => p.risks.map((r) => ({ svc: p.entity, ...r })));
  const critical = risks.filter((r) => r.score >= 0.7);
  const singleOwner = profiles.filter((p) => p.knowledge.effective_owners < 1.6 && p.knowledge.top.length > 0);
  const topBus = [...org].sort((a, b) => b.critical_services - a.critical_services)[0];
  return {
    services: profiles.length,
    risks: risks.length,
    criticalRisks: critical.length,
    singleOwnerServices: singleOwner.length,
    highestBusRisk: topBus ?? null,
    avgEffectiveOwners:
      profiles.length === 0
        ? 0
        : Math.round(
            (profiles.reduce((s, p) => s + p.knowledge.effective_owners, 0) / profiles.length) * 100,
          ) / 100,
  };
}
