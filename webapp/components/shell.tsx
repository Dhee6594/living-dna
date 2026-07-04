"use client";
/** Application shell: sidebar navigation, topbar with repo selector,
 *  global search (Cmd/Ctrl-K), theme toggle, auth chip. */
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "@/lib/api";
import { useAuth, usePrefs } from "@/lib/store";
import type { SearchHit } from "@/lib/types";

const NAV = [
  { href: "/", label: "Dashboard", icon: "◈" },
  { href: "/genome", label: "Genome", icon: "🧬" },
  { href: "/knowledge", label: "Knowledge Graph", icon: "◉" },
  { href: "/archaeology", label: "Archaeology", icon: "⌖" },
  { href: "/timetravel", label: "Time Travel", icon: "◷" },
  { href: "/busfactor", label: "Bus Factor", icon: "▣" },
  { href: "/risk", label: "Risk", icon: "△" },
  { href: "/executive", label: "Executive", icon: "◫" },
  { href: "/search", label: "Search", icon: "⌕" },
  { href: "/settings", label: "Settings", icon: "⚙" },
] as const;

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { theme } = usePrefs();
  const [navOpen, setNavOpen] = useState(false);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("light", theme === "light");
    root.classList.toggle("dark", theme === "dark");
  }, [theme]);

  return (
    <div className="flex min-h-screen">
      {/* Sidebar (responsive: overlay < md) */}
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-panel focus:p-2"
      >
        Skip to content
      </a>
      <nav
        aria-label="Primary"
        className={`fixed inset-y-0 left-0 z-40 w-56 transform border-r border-edge bg-panel p-3 transition-transform md:static md:translate-x-0 ${
          navOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <Link href="/" className="mb-6 flex items-center gap-2 px-2 pt-1">
          <span aria-hidden className="text-lg">🧬</span>
          <span className="font-semibold tracking-tight">Living DNA</span>
        </Link>
        <ul className="space-y-0.5">
          {NAV.map((item) => {
            const active =
              item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  onClick={() => setNavOpen(false)}
                  className={`flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-sm transition-colors ${
                    active
                      ? "bg-accent/15 font-medium text-accent"
                      : "text-muted hover:bg-edge/40 hover:text-ink"
                  }`}
                >
                  <span aria-hidden className="w-4 text-center">{item.icon}</span>
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onMenu={() => setNavOpen((v) => !v)} />
        <main id="main" className="mx-auto w-full max-w-6xl flex-1 p-4 md:p-6">
          {children}
        </main>
      </div>
      <CommandPalette />
    </div>
  );
}

function Topbar({ onMenu }: { onMenu: () => void }) {
  const { theme, toggleTheme, repo, setRepo } = usePrefs();
  const { user, signOut } = useAuth();
  const [repos, setRepos] = useState<string[]>([]);

  useEffect(() => {
    api.report().then((r) => setRepos(Object.keys(r.by_repo))).catch(() => {});
  }, []);

  return (
    <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-edge bg-surface/80 px-4 py-2.5 backdrop-blur">
      <button
        onClick={onMenu}
        aria-label="Toggle navigation"
        className="rounded-lg border border-edge px-2 py-1 text-sm md:hidden"
      >
        ☰
      </button>

      {/* Repository selector */}
      <label className="flex items-center gap-2 text-sm text-muted">
        <span className="hidden sm:inline">Repo</span>
        <select
          value={repo ?? ""}
          onChange={(e) => setRepo(e.target.value || null)}
          className="rounded-lg border border-edge bg-panel px-2 py-1 text-sm text-ink"
          aria-label="Repository filter"
        >
          <option value="">All repositories</option>
          {repos.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
      </label>

      <div className="ml-auto flex items-center gap-2">
        <kbd className="hidden rounded border border-edge px-1.5 py-0.5 text-xs text-muted lg:inline">
          ⌘K search
        </kbd>
        <button
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
          className="rounded-lg border border-edge px-2.5 py-1 text-sm hover:bg-edge/40"
        >
          {theme === "dark" ? "☀" : "☾"}
        </button>
        {user ? (
          <button
            onClick={signOut}
            title="Sign out"
            className="rounded-lg border border-edge px-2.5 py-1 text-sm hover:bg-edge/40"
          >
            {user.name.split(" ")[0]} ↩
          </button>
        ) : (
          <Link
            href="/login"
            className="rounded-lg bg-accent/15 px-2.5 py-1 text-sm font-medium text-accent"
          >
            Sign in
          </Link>
        )}
      </div>
    </header>
  );
}

function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const router = useRouter();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (!q) return setHits([]);
    const t = setTimeout(() => api.search(q).then(setHits).catch(() => setHits([])), 150);
    return () => clearTimeout(t);
  }, [q]);

  const go = useCallback(
    (hit: SearchHit) => {
      setOpen(false);
      setQ("");
      if (hit.kind === "Service") router.push(`/genome?focus=${hit.id}`);
      else if (hit.kind === "Person") router.push(`/busfactor?person=${hit.name}`);
      else router.push(`/search?q=${encodeURIComponent(hit.name)}`);
    },
    [router],
  );

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 bg-black/50 p-4 pt-24"
          onClick={() => setOpen(false)}
          role="dialog"
          aria-modal="true"
          aria-label="Global search"
        >
          <motion.div
            initial={{ y: -12, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: -12, opacity: 0 }}
            className="mx-auto max-w-lg overflow-hidden rounded-xl border border-edge bg-panel shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <input
              autoFocus
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search services, people, eras…"
              aria-label="Search the genome"
              className="w-full border-b border-edge bg-transparent px-4 py-3 text-sm outline-none"
            />
            <ul className="max-h-72 overflow-y-auto p-1">
              {hits.map((h) => (
                <li key={h.id}>
                  <button
                    onClick={() => go(h)}
                    className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm hover:bg-edge/40"
                  >
                    <span className="text-xs text-muted">{h.kind}</span>
                    <span>{h.name}</span>
                    <span className="ml-auto font-mono text-xs text-muted">{h.id}</span>
                  </button>
                </li>
              ))}
              {q && hits.length === 0 && (
                <li className="px-3 py-4 text-center text-sm text-muted">No matches</li>
              )}
            </ul>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
