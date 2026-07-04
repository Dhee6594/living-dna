import { describe, expect, it } from "vitest";
import { ownershipHealth, pct, riskTone, shortHash, tsToDate } from "@/lib/format";

describe("format helpers", () => {
  it("pct rounds to whole percents", () => {
    expect(pct(0.984)).toBe("98%");
    expect(pct(0)).toBe("0%");
    expect(pct(1)).toBe("100%");
  });

  it("tsToDate converts unix seconds to ISO date", () => {
    expect(tsToDate(1577836800)).toBe("2020-01-01");
  });

  it("riskTone thresholds match the genome's scoring bands", () => {
    expect(riskTone(0.9)).toBe("bad");
    expect(riskTone(0.5)).toBe("warn");
    expect(riskTone(0.1)).toBe("good");
  });

  it("ownershipHealth mirrors the 1.6 knowledge-concentration line", () => {
    expect(ownershipHealth(1.0)).toBe("bad");
    expect(ownershipHealth(1.8)).toBe("warn");
    expect(ownershipHealth(3.2)).toBe("good");
  });

  it("shortHash truncates safely", () => {
    expect(shortHash("abcdef1234567890")).toBe("abcdef12");
    expect(shortHash(undefined)).toBe("");
  });
});
