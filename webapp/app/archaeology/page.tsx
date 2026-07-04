"use client";
/** Architecture Archaeology — evidence-cited Q&A over the genome. */
import { FormEvent, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "@/lib/api";
import { Card, ErrorNote, PageHeader } from "@/components/ui";
import type { AskAnswer } from "@/lib/types";

const SUGGESTIONS = [
  "who knows payments",
  "why does checkout depend on payments",
  "why does notifications exist",
  "what happens if Lena leaves",
];

export default function ArchaeologyPage() {
  const [q, setQ] = useState("");
  const [history, setHistory] = useState<{ q: string; a: AskAnswer }[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function ask(question: string) {
    setBusy(true);
    setError(null);
    try {
      const a = await api.ask(question);
      setHistory((h) => [{ q: question, a }, ...h]);
      setQ("");
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (q.trim()) void ask(q.trim());
  }

  return (
    <>
      <PageHeader
        title="Architecture archaeology"
        sub="Ask the genome. Every answer cites its evidence — commits, edges, provenance."
      />
      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="why does checkout depend on payments…"
          aria-label="Question for the genome"
          className="flex-1 rounded-lg border border-edge bg-panel px-3 py-2 text-sm"
        />
        <button
          disabled={busy || !q.trim()}
          className="rounded-lg bg-accent/15 px-4 py-2 text-sm font-medium text-accent disabled:opacity-50"
        >
          {busy ? "Digging…" : "Ask"}
        </button>
      </form>
      <div className="mt-2 flex flex-wrap gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => void ask(s)}
            className="rounded-full border border-edge px-2.5 py-1 text-xs text-muted hover:text-ink"
          >
            {s}
          </button>
        ))}
      </div>

      {error != null && <div className="mt-4"><ErrorNote error={error} /></div>}

      <AnimatePresence>
        {history.map((h, i) => (
          <motion.div
            key={history.length - i}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4"
          >
            <Card>
              <div className="text-xs font-medium uppercase tracking-wide text-muted">{h.q}</div>
              <p className="mt-2 text-sm leading-relaxed">{h.a.answer}</p>
              {h.a.evidence.length > 0 && (
                <ul className="mt-3 space-y-1 border-t border-edge/60 pt-2">
                  {h.a.evidence.map((e, j) => (
                    <li key={j} className="font-mono text-xs text-muted">⌖ {e}</li>
                  ))}
                </ul>
              )}
              {h.a.hint && <p className="mt-2 text-xs italic text-muted">{h.a.hint}</p>}
            </Card>
          </motion.div>
        ))}
      </AnimatePresence>
    </>
  );
}
