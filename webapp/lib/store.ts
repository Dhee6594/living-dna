"use client";
/** Global client state: theme, repo filter, auth placeholder, preferences. */
import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Theme = "dark" | "light";

interface PrefsState {
  theme: Theme;
  reducedMotion: boolean;
  repo: string | null; // active repository filter (null = all)
  setTheme: (t: Theme) => void;
  toggleTheme: () => void;
  setReducedMotion: (v: boolean) => void;
  setRepo: (r: string | null) => void;
}

export const usePrefs = create<PrefsState>()(
  persist(
    (set, get) => ({
      theme: "dark",
      reducedMotion: false,
      repo: null,
      setTheme: (theme) => set({ theme }),
      toggleTheme: () => set({ theme: get().theme === "dark" ? "light" : "dark" }),
      setReducedMotion: (reducedMotion) => set({ reducedMotion }),
      setRepo: (repo) => set({ repo }),
    }),
    { name: "dna-prefs" },
  ),
);

/** Auth placeholder — real SSO/RBAC arrives in the Enterprise phase.
 *  Shapes the UI contract now so wiring auth later is non-breaking. */
interface AuthState {
  user: { name: string; email: string } | null;
  signIn: (name: string, email: string) => void;
  signOut: () => void;
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      signIn: (name, email) => set({ user: { name, email } }),
      signOut: () => set({ user: null }),
    }),
    { name: "dna-auth" },
  ),
);

/** Pure helper (unit-tested): filter profiles by active repo. */
export function filterByRepo<T extends { repo: string | null }>(
  items: T[],
  repo: string | null,
): T[] {
  return repo ? items.filter((i) => i.repo === repo) : items;
}
