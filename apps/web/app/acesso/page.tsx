import Link from "next/link";
import { redirect } from "next/navigation";

import { getAccessResolution, getPendingInvitations } from "../../lib/bcos-api";
import { auth } from "../../lib/auth/server";
import { SessionControls } from "../../components/session-controls";

export const dynamic = "force-dynamic";

export default async function AccessPage() {
  const { data: session } = await auth.getSession();
  if (!session?.user) redirect("/auth/sign-in");

  let access;
  let invitations;

  try {
    [access, invitations] = await Promise.all([
      getAccessResolution(),
      getPendingInvitations(),
    ]);
  } catch (error) {
    console.error(
      "BCOS access resolution failed after authenticated Neon session:",
      error instanceof Error ? error.message : "unknown error",
    );

    return (
      <main className="auth-shell">
        <section className="auth-brand">
          <span>HPTECH PLATFORM</span>
          <h1>Beauty Coworking OS</h1>
          <p>Sua autenticação foi concluída com segurança.</p>
        </section>
        <section className="auth-card">
          <h2>Acesso temporariamente indisponível</h2>
          <p>
            Sua sessão está autenticada, mas não foi possível consultar suas
            permissões no BCOS neste momento.
          </p>
          <p>Tente novamente em alguns instantes.</p>
          <p><Link href="/acesso">Tentar novamente</Link></p>
        </section>
      </main>
    );
  }

  const destinations = [
    ...(access.platform_destination ? [{ label: "Administração HPTECH", href: access.platform_destination }] : []),
    ...access.tenants.map((tenant) => ({
      label: `${tenant.tenant_name} — ${tenant.role}`,
      href: `/acesso/tenant/${encodeURIComponent(tenant.tenant_id)}`,
    })),
  ];

  if (destinations.length === 1 && invitations.length === 0) redirect(destinations[0].href);

  return (
    <main className="auth-shell">
      <section className="auth-brand">
        <span>HPTECH PLATFORM</span>
        <h1>Beauty Coworking OS</h1>
        <p>Escolha o ambiente autorizado para sua identidade.</p>
      </section>
      <section className="auth-card">
        <div className="access-session"><SessionControls label={session.user.name || session.user.email || "Usuário autenticado"} /></div>
        <div className="access-panel">
          <div className="access-heading"><span>SEUS ACESSOS</span><h2>Escolha onde deseja entrar.</h2><p>Ambientes liberados para a sua conta no Beauty Coworking OS.</p></div>
          {destinations.length > 0 && <div className="access-list">{destinations.map((item) => <Link className="access-item" key={item.label} href={item.href}><span>{item.label}</span><strong>Entrar →</strong></Link>)}</div>}
          {destinations.length === 0 && invitations.length === 0 ? <div className="access-empty"><strong>Nenhum acesso disponível</strong><span>Quando um ambiente for liberado para sua conta, ele aparecerá aqui.</span></div> : null}
          {invitations.length > 0 && <div className="invitation-block"><div><span>CONVITE PENDENTE</span><h3>Finalize seu acesso</h3><p>Você recebeu permissão para entrar em um ambiente BCOS.</p></div>{invitations.map((invitation) => <Link className="invitation-action" key={invitation.id} href={`/acesso/convites/${invitation.id}`}><span>Perfil {invitation.role}</span><strong>Revisar convite →</strong></Link>)}</div>}
        </div>
      </section>
    </main>
  );
}
