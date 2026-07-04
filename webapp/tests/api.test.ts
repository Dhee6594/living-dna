import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, executiveSummary } from "@/lib/api";
import type { OrgBusFactorRow, Profile } from "@/lib/types";

const profile = (over: Partial<Profile>): Profile => ({
  entity: "svc", id: "svc:svc", kind: "Service", repo: "r", dir: "svc",
  languages: {}, born: null, eras: [], dependencies: [], dependents: [],
  co_changes_with: [], knowledge: { effective_owners: 2, top: [] },
  risks: [], stats: { lifetime_commits: 1 },
  ...over,
});

afterEach(() => vi.unstubAllGlobals());

describe("api client", () => {
  it("hits the expected endpoint and parses JSON", async () => {
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify([{ id: "svc:payments", kind: "Service", name: "payments" }])),
    );
    vi.stubGlobal("fetch", fetchMock);
    const hits = await api.search("pay");
    expect(fetchMock).toHaveBeenCalledWith("/api/search?q=pay", expect.anything());
    expect(hits[0].id).toBe("svc:payments");
  });

  it("throws ApiError with status on non-2xx", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("nope", { status: 404 })));
    await expect(api.profile("ghost")).rejects.toMatchObject({ status: 404 });
    await expect(api.profile("ghost")).rejects.toBeInstanceOf(ApiError);
  });

  it("encodes query parameters", async () => {
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) => new Response("{}"));
    vi.stubGlobal("fetch", fetchMock);
    await api.ask("why does a depend on b?");
    expect(fetchMock.mock.calls[0]?.[0]).toContain("why%20does%20a%20depend%20on%20b%3F");
  });
});

describe("executiveSummary", () => {
  const org: OrgBusFactorRow[] = [
    { person: "Lena", person_id: "person:l", critical_services: 2, services_impacted: 3 },
    { person: "Jin", person_id: "person:j", critical_services: 0, services_impacted: 1 },
  ];

  it("aggregates risks and ownership from profiles", () => {
    const s = executiveSummary(
      [
        profile({ risks: [{ class: "bottleneck", score: 0.8, note: "", evidence: [] }] }),
        profile({
          entity: "b", id: "svc:b",
          knowledge: { effective_owners: 1.1, top: [{ person: "Lena", person_id: "p", weight: 0.9 }] },
        }),
      ],
      org,
    );
    expect(s.services).toBe(2);
    expect(s.criticalRisks).toBe(1);
    expect(s.singleOwnerServices).toBe(1);
    expect(s.highestBusRisk?.person).toBe("Lena");
    expect(s.avgEffectiveOwners).toBeCloseTo(1.55, 2);
  });

  it("handles the empty genome", () => {
    const s = executiveSummary([], []);
    expect(s.services).toBe(0);
    expect(s.avgEffectiveOwners).toBe(0);
    expect(s.highestBusRisk).toBeNull();
  });
});
