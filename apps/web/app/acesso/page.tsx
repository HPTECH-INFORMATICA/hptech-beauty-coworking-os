import Link from "next/link";
import { redirect } from "next/navigation";

import { getAccessResolution, getPendingInvitations } from "../../lib/bcos-api";
import { auth } from "../../lib/auth/server";

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
        <h2>Acessos disponíveis</h2>
        {destinations.length === 0 ? <p>Nenhum acesso ativo encontrado.</p> : (
          <div>
            {destinations.map((item) => <p key={item.label}><Link href={item.href}>{item.label}</Link></p>)}
          </div>
        )}
        {invitations.length > 0 && (
          <div>
            <h3>Convites pendentes</h3>
            {invitations.map((invitation) => (
              <p key={invitation.id}>
                {invitation.role} — <Link href={`/acesso/convites/${invitation.id}`}>Aceitar convite</Link>
              </p>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
