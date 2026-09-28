"use client";

import { useState } from "react";
import { authClient } from "../../lib/auth/client";

export function LogoutButton() {
  const [pending, setPending] = useState(false);

  async function logout() {
    setPending(true);
    try {
      await authClient.signOut();
      window.location.assign("/auth/sign-in");
    } finally {
      setPending(false);
    }
  }

  return <button type="button" className="auth-logout" onClick={logout} disabled={pending}>{pending ? "Saindo..." : "Sair"}</button>;
}
