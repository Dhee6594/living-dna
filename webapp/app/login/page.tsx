"use client";
/** Authentication placeholder — establishes the auth UI contract now;
 *  real SSO/SAML lands in the Enterprise phase without breaking callers. */
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { useAuth } from "@/lib/store";
import { Card } from "@/components/ui";

export default function LoginPage() {
  const { signIn } = useAuth();
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    signIn(name.trim(), email.trim());
    router.push("/");
  }

  return (
    <div className="mx-auto mt-16 max-w-sm">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <Card>
          <h1 className="text-lg font-semibold">Sign in</h1>
          <p className="mt-1 text-sm text-muted">
            Local placeholder — SSO/SAML arrives with the Enterprise edition.
          </p>
          <form onSubmit={onSubmit} className="mt-4 space-y-3">
            <label className="block text-sm">
              <span className="mb-1 block text-xs text-muted">Name</span>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="w-full rounded-lg border border-edge bg-surface px-3 py-2 text-sm"
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block text-xs text-muted">Email</span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-edge bg-surface px-3 py-2 text-sm"
              />
            </label>
            <button className="w-full rounded-lg bg-accent/20 py-2 text-sm font-medium text-accent">
              Continue
            </button>
          </form>
        </Card>
      </motion.div>
    </div>
  );
}
