"use client";

import { AuthView } from "@neondatabase/auth-ui";
import { useParams } from "next/navigation";

export default function AuthPage() {
  const params = useParams<{ path: string }>();
  return (
    <main className="auth-shell">
      <section className="auth-brand">
        <span>HPTECH PLATFORM</span>
        <h1>Beauty Coworking OS</h1>
        <p>Acesso seguro para administração, recepção e profissionais.</p>
      </section>
      <section className="auth-card">
        <AuthView path={params.path} redirectTo="/acesso" />
      </section>
    </main>
  );
}
