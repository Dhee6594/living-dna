"use client";
/** Reusable UI primitives. Kept in one module deliberately — they share
 *  motion presets and theme tokens; split when any grows past ~50 lines. */
import { motion } from "framer-motion";
import { usePrefs } from "@/lib/store";
import type { ReactNode } from "react";

export const rise = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.25, ease: "easeOut" as const },
};

export function PageHeader({ title, sub }: { title: string; sub?: string }) {
  return (
    <motion.header {...rise} className="mb-6">
      <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
      {sub && <p className="mt-1 text-sm text-muted">{sub}</p>}
    </motion.header>
  );
}

export function Card({
  children,
  className = "",
  as: Tag = "section",
  role,
}: {
  children: ReactNode;
  className?: string;
  as?: "section" | "article" | "div";
  role?: string;
}) {
  return (
    <Tag role={role} className={`rounded-xl border border-edge bg-panel p-4 ${className}`}>
      {children}
    </Tag>
  );
}

export function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: ReactNode;
  tone?: "good" | "warn" | "bad";
}) {
  const toneCls =
    tone === "bad" ? "text-bad" : tone === "warn" ? "text-warn" : tone === "good" ? "text-good" : "";
  return (
    <Card className="min-w-0">
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
      <div className={`mt-1 truncate text-2xl font-semibold tabular-nums ${toneCls}`}>{value}</div>
    </Card>
  );
}

export function Badge({
  tone = "good",
  children,
}: {
  tone?: "good" | "warn" | "bad" | "muted";
  children: ReactNode;
}) {
  const cls = {
    good: "bg-good/15 text-good",
    warn: "bg-warn/15 text-warn",
    bad: "bg-bad/15 text-bad",
    muted: "bg-edge/60 text-muted",
  }[tone];
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {children}
    </span>
  );
}

export function Skeleton({ className = "h-24" }: { className?: string }) {
  const reduced = usePrefs((s) => s.reducedMotion);
  return (
    <div
      aria-hidden
      className={`rounded-xl border border-edge bg-panel ${className} ${reduced ? "" : "animate-pulse"}`}
    />
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <Card className="py-10 text-center text-sm text-muted" role="status">
      {children}
    </Card>
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  return (
    <Card className="border-bad/40 text-sm" role="alert">
      <span className="font-medium text-bad">Couldn&apos;t reach the genome API.</span>{" "}
      <span className="text-muted">
        Start it with <code className="font-mono">dna serve</code> ({String(error)})
      </span>
    </Card>
  );
}
