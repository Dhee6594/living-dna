"use client";
/** Search — full-page genome search (services, people, eras, decisions). */
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { Card, Empty, ErrorNote, PageHeader, Skeleton } from "@/components/ui";
import type { SearchHit } from "@/lib/types";

function SearchInner() {
  const initial = useSearchParams().get("q") ?? "";
  const [q, setQ] = useState(initial);
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (!q) return setHits([]);
    const t = setTimeout(
      () => api.search(q).then(setHits).catch(setError),
      200,
    );
    return () => clearTimeout(t);
  }, [q]);

  if (error) return <ErrorNote error={error} />;

  return (
    <>
      <PageHeader title="Search the genome" sub="Services, people, eras, decisions — by name or id." />
      <input
        autoFocus
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="payments, Lena, era…"
        aria-label="Search query"
        className="w-full max-w-lg rounded-lg border border-edge bg-panel px-4 py-2.5 text-sm"
      />
      <div className="mt-4">
        {hits === null ? (
          <Skeleton className="h-40" />
        ) : hits.length === 0 ? (
          q ? <Empty>No matches for “{q}”.</Empty> : null
        ) : (
          <Card>
            <ul className="divide-y divide-edge/60">
              {hits.map((h) => (
                <li key={h.id} className="flex items-center gap-3 py-2 text-sm">
                  <span className="w-16 text-xs uppercase tracking-wide text-muted">{h.kind}</span>
                  {h.kind === "Service" ? (
                    <Link href={`/genome?focus=${h.id}`} className="font-medium hover:text-accent">
                      {h.name}
                    </Link>
                  ) : h.kind === "Person" ? (
                    <Link href={`/busfactor?person=${h.name}`} className="font-medium hover:text-accent">
                      {h.name}
                    </Link>
                  ) : (
                    <span className="font-medium">{h.name}</span>
                  )}
                  <span className="ml-auto font-mono text-xs text-muted">{h.id}</span>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    </>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<Skeleton className="h-40" />}>
      <SearchInner />
    </Suspense>
  );
}
