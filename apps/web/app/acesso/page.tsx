import Link from "next/link";
import { redirect } from "next/navigation";

import { getAccessResolution, getPendingInvitations, getPendingProfessionalInvitations, getPendingTeamInvitations } from "../../lib/bcos-api";
import { auth } from "../../lib/auth/server";
import { SessionControls } from "../../components/session-controls";

export const dynamic = "force-dynamic";

export default async function AccessPage({ searchParams }: { searchParams?: Promise<{ invitationAccepted?: string; selectionError?: string }> }) {
  const query = searchParams ? await searchParams : {};
  const { data: session } = await auth.getSession();
  if (!session?.user) redirect("/auth/sign-in");

  const results = await Promise.allSettled([
    getAccessResolution(),
    getPendingInvitations(),
    getPendingProfessionalInvitations(),
    getPendingTeamInvitations(),
  ]);

  const [accessResult, invitationsResult, professionalResult, teamResult] = results;
  for (const [operation, result] of [
    ["access", accessResult],
    ["membership invitations", invitationsResult],
    ["professional invitations", professionalResult],
    ["team invitations", teamResult],
  ] as const) {
    if (result.status === "rejected") {
      console.error(
        `BCOS ${operation} lookup failed after authenticated Neon session:`,
        result.reason instanceof Error ? result.reason.message : "unknown error",
      );
    }
  }

  let access = accessResult.status === "fulfilled"
    ? accessResult.value
    : { platform_destination: null, tenants: [] };
  const invitations = invitationsResult.status === "fulfilled" ? invitationsResult.value : [];
  const professionalInvitations = professionalResult.status === "fulfilled" ? professionalResult.value : [];
  const teamInvitations = teamResult.status === "fulfilled" ? teamResult.value : [];

  if (teamResult.status === "fulfilled" && access.tenants.length === 0) {
    try {
      access = await getAccessResolution();
    } catch (error) {
      console.error(
        "BCOS access refresh failed after team invitation activation:",
        error instanceof Error ? error.message : "unknown error",
      );
    }
  }

  const allLookupsFailed = results.every((result) => result.status === "rejected");
  if (allLookupsFailed) {
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
            Sua sessão está autenticada, mas não foi possível consultar seus
            acessos no BCOS neste momento.
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

  if (destinations.length === 1 && invitations.length === 0 && professionalInvitations.length === 0 && teamInvitations.length === 0) redirect(destinations[0].href);

  return (
    <main className="auth-shell">
      <section className="auth-brand">
        <span>HPTECH PLATFORM</span>
        <h1>Beauty Coworking OS</h1>
        <p>Acesse diretamente os ambientes liberados para sua conta.</p>
      </section>
      <section className="auth-card">
        <div className="access-session"><SessionControls label={session.user.name || session.user.email || "Usuário autenticado"} /></div>
        <div className="access-panel">
          {query.invitationAccepted === "pendingActivation" ? <div className="access-notice"><strong>Convite aceito com sucesso.</strong><span>Seu vínculo já está ativo. O ambiente do cliente ainda aguarda liberação comercial pela HPTECH PLATFORM e aparecerá aqui assim que for ativado.</span></div> : null}
          {query.selectionError === "1" ? <div className="access-notice"><strong>Este ambiente não está disponível para entrada.</strong><span>Atualizamos seus acessos. Se o ambiente ainda estiver aguardando ativação ou sua permissão tiver mudado, ele não será aberto.</span></div> : null}
          <div className="access-heading"><span>SEUS ACESSOS</span><h2>Seus ambientes.</h2><p>O BCOS direciona sua conta conforme o acesso definido pelo contratante.</p></div>
          {destinations.length > 0 && <div className="access-list">{destinations.map((item) => <Link className="access-item" key={item.label} href={item.href}><span>{item.label}</span><strong>Entrar →</strong></Link>)}</div>}
          {destinations.length === 0 && invitations.length === 0 && professionalInvitations.length === 0 && teamInvitations.length === 0 ? <div className="access-empty"><strong>Nenhum acesso disponível</strong><span>Quando um ambiente for liberado para sua conta, ele aparecerá aqui.</span></div> : null}
          {teamInvitations.length > 0 && <div className="invitation-block"><div><span>CONVITE DA EQUIPE</span><h3>Você foi convidado para uma equipe</h3><p>Revise o negócio e o papel antes de liberar seu acesso.</p></div>{teamInvitations.map((invitation) => <Link className="invitation-action" key={invitation.id} href={`/acesso/equipe/${invitation.id}`}><span>{invitation.tenant_name}</span><strong>{invitation.display_name} · {invitation.role} →</strong></Link>)}</div>}{invitations.length > 0 && <div className="invitation-block"><div><span>CONVITE PENDENTE</span><h3>Finalize seu acesso</h3><p>Você recebeu permissão para entrar em um ambiente BCOS.</p></div>{invitations.map((invitation) => <Link className="invitation-action" key={invitation.id} href={`/acesso/convites/${invitation.id}`}><span>Perfil {invitation.role}</span><strong>Revisar convite →</strong></Link>)}</div>}{professionalInvitations.length > 0 && <div className="invitation-block"><div><span>CONVITE PROFISSIONAL</span><h3>Seu portal profissional está disponível</h3><p>Revise o vínculo com a unidade antes de liberar seu acesso.</p></div>{professionalInvitations.map((invitation) => <Link className="invitation-action" key={invitation.id} href={`/acesso/profissionais/${invitation.id}`}><span>{invitation.tenant_name}</span><strong>{invitation.professional_name} · Revisar →</strong></Link>)}</div>}
          
        </div>
      </section>
    </main>
  );
}
