"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function EnvironmentSwitch() {
  const router = useRouter();
  const [pending, setPending] = useState(false);

  async function switchEnvironment() {
    setPending(true);
    try {
      const response = await fetch("/api/session/tenant", { method: "POST" });
      if (!response.ok) throw new Error("Não foi possível limpar o ambiente selecionado.");
      router.push("/acesso");
      router.refresh();
    } finally {
      setPending(false);
    }
  }

  return (
    <button className="bcos-environment-switch" type="button" onClick={switchEnvironment} disabled={pending}>
      {pending ? "Trocando..." : "Trocar ambiente"}
    </button>
  );
}
