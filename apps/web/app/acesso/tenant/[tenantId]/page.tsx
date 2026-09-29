import Link from "next/link";
import { redirect } from "next/navigation";

import { getAccessResolution, persistSelectedTenant } from "../../../../lib/bcos-api";
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
  let pendingTenantName = "sua empresa";
  let selectedDestination: string | null = null;
  try {
    const resolution = await getAccessResolution();
    const accessTenant = resolution.tenants.find((item) => item.tenant_id === tenantId);
    pendingTenantName = accessTenant?.tenant_name || pendingTenantName;
    if (accessTenant) {
      const selected = await persistSelectedTenant(tenantId);
      selectedDestination = selected.destination;
    }
  } catch (error) {
    console.error(
      "BCOS tenant selection failed:",
      error instanceof Error ? error.message : "unknown error",
    );
  }

  if (selectedDestination) redirect(selectedDestination);

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
          <h1>Acesso confirmado.</h1>
          <p>Seu perfil de proprietário foi confirmado para <strong>{pendingTenantName}</strong>. A liberação comercial da empresa está em conclusão pela HPTECH PLATFORM.</p>
          <div className="invitation-role"><span>PRÓXIMA ETAPA</span><strong>LIBERAÇÃO DA EMPRESA</strong></div>
          <p>Você não precisa criar outra conta, aceitar outro convite ou repetir este processo.</p>
          <Link className="activation-return" href="/acesso">Ir para meus acessos</Link>
        </div>
      </section>
    </main>
  );
}
