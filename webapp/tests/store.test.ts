import { describe, expect, it } from "vitest";
import { filterByRepo } from "@/lib/store";

describe("filterByRepo", () => {
  const items = [
    { repo: "acme-shop", name: "payments" },
    { repo: "career-ops", name: "modes" },
    { repo: null, name: "orphan" },
  ];

  it("returns everything when no repo selected", () => {
    expect(filterByRepo(items, null)).toHaveLength(3);
  });

  it("filters to the active repo", () => {
    const out = filterByRepo(items, "acme-shop");
    expect(out).toHaveLength(1);
    expect(out[0].name).toBe("payments");
  });

  it("matches nothing for unknown repo", () => {
    expect(filterByRepo(items, "ghost")).toHaveLength(0);
  });
});
