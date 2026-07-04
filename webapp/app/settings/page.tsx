"use client";
/** Settings & user preferences (persisted client-side via zustand). */
import { usePrefs } from "@/lib/store";
import { Card, PageHeader } from "@/components/ui";

export default function SettingsPage() {
  const { theme, setTheme, reducedMotion, setReducedMotion, repo, setRepo } = usePrefs();

  return (
    <>
      <PageHeader title="Settings" sub="Preferences persist in this browser." />
      <div className="max-w-lg space-y-4">
        <Card>
          <h2 className="mb-3 text-sm font-medium">Appearance</h2>
          <div role="radiogroup" aria-label="Theme" className="flex gap-2">
            {(["dark", "light"] as const).map((t) => (
              <button
                key={t}
                role="radio"
                aria-checked={theme === t}
                onClick={() => setTheme(t)}
                className={`rounded-lg border px-4 py-2 text-sm capitalize ${
                  theme === t ? "border-accent text-accent" : "border-edge text-muted"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
          <label className="mt-4 flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={reducedMotion}
              onChange={(e) => setReducedMotion(e.target.checked)}
            />
            Reduce motion (also honours your OS setting automatically)
          </label>
        </Card>

        <Card>
          <h2 className="mb-3 text-sm font-medium">Data</h2>
          <p className="text-sm text-muted">
            Active repository filter: <span className="text-ink">{repo ?? "all"}</span>
            {repo && (
              <button onClick={() => setRepo(null)} className="ml-2 text-accent underline">
                clear
              </button>
            )}
          </p>
          <p className="mt-2 text-sm text-muted">
            The genome API is read-only; corrections and connector settings arrive with
            the enterprise control plane.
          </p>
        </Card>
      </div>
    </>
  );
}
