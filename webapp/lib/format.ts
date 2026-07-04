/** Small pure formatting helpers (unit-tested). */

export function pct(w: number): string {
  return `${Math.round(w * 100)}%`;
}

export function tsToDate(ts: number): string {
  return new Date(ts * 1000).toISOString().slice(0, 10);
}

export function riskTone(score: number): "good" | "warn" | "bad" {
  if (score >= 0.7) return "bad";
  if (score >= 0.4) return "warn";
  return "good";
}

export function shortHash(h?: string): string {
  return h ? h.slice(0, 8) : "";
}

/** Effective owners < 1.6 is the genome's knowledge-concentration line. */
export function ownershipHealth(effectiveOwners: number): "good" | "warn" | "bad" {
  if (effectiveOwners >= 2.5) return "good";
  if (effectiveOwners >= 1.6) return "warn";
  return "bad";
}
