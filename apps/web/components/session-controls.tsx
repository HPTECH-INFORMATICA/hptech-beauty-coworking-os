"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { authClient } from "../lib/auth/client";

export function SessionControls({ label }: { label: string }) {
  const [pending, setPending] = useState(false);
  const router = useRouter();

  async function logout() {
    setPending(true);
    try {
      await authClient.signOut();
      router.replace("/auth/sign-in");
      router.refresh();
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="session-controls">
      <span>Conectado como</span>
      <strong>{label}</strong>
      <button type="button" onClick={logout} disabled={pending}>
        {pending ? "Saindo..." : "Sair"}
      </button>
    </div>
  );
}
