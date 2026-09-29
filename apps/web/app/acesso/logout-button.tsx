"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { authClient } from "../../lib/auth/client";

export function LogoutButton() {
  const [pending, setPending] = useState(false);
  const router = useRouter();

  async function logout() {
    setPending(true);
    try {
      await Promise.all([authClient.signOut(), fetch("/api/session/tenant", { method: "POST" })]);
      router.replace("/auth/sign-in");
      router.refresh();
    } finally {
      setPending(false);
    }
  }

  return <button type="button" className="auth-logout" onClick={logout} disabled={pending}>{pending ? "Saindo..." : "Sair"}</button>;
}
