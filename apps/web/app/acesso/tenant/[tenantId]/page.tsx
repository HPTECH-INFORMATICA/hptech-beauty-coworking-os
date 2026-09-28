import Link from "next/link";
import { redirect } from "next/navigation";

import { persistSelectedTenant } from "../../../../lib/bcos-api";
import { auth } from "../../../../lib/auth/server";
import { SessionControls } from "../../../../components/session-controls";

export const dynamic = "force-dynamic";

export default async function SelectTenantPage({
  params,
}: {
  params: Promise<{ tenantId: string }>;
}) {
  const { data: session } = await auth.getSession();
  if (!session?.user) redirect("/auth/sign-in");

  const { tenantId } = await params;
  try {
    const tenant = await persistSelectedTenant(tenantId);
    redirect(tenant.destination);
  } catch (error) {
    console.error(
      "BCOS tenant selection failed:",
      error instanceof Error ? error.message : "unknown error",
    );
  }

  return (
    <main className="auth-shell">
      <section className="auth-brand">
        <span>HPTECH PLATFORM</span>
        <h1>Beauty Coworking OS</h1>
        <p>Seu acesso foi confirmado com segurança.</p>
      </section>
      <section className="auth-card">
        <div className="access-session">
          <SessionControls label={session.user.name || session.user.email || "Usuário autenticado"} />
        </div>
        <div className="invitation-card">
          <span className="invitation-eyebrow">ATIVAÇÃO DO CONTRATANTE</span>
          <h1>Seu convite foi aceito.</h1>
          <p>A HPTECH ainda precisa concluir a ativação da empresa. Assim que o contratante estiver ativo, seu painel administrativo será liberado.</p>
          <div className="invitation-role"><span>STATUS</span><strong>AGUARDANDO ATIVAÇÃO</strong></div>
          <Link className="activation-return" href="/acesso">Voltar aos acessos</Link>
        </div>
      </section>
    </main>
  );
}
