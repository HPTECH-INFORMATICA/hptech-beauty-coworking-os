import { redirect } from "next/navigation";

import { getPendingInvitations } from "../../../../lib/bcos-api";
import { auth } from "../../../../lib/auth/server";
import { acceptPendingInvitation } from "../actions";
import { SessionControls } from "../../../../components/session-controls";

export const dynamic = "force-dynamic";

export default async function InvitationPage({ params }: { params: Promise<{ id: string }> }) {
  const { data: session } = await auth.getSession();
  if (!session?.user) redirect("/auth/sign-in");
  const { id } = await params;
  const invitations = await getPendingInvitations();
  const invitation = invitations.find((item) => item.id === id);
  if (!invitation) redirect("/acesso");

  return (
    <main className="auth-shell">
      <section className="auth-brand">
        <span>HPTECH PLATFORM</span>
        <h1>Beauty Coworking OS</h1>
        <p>Ativação segura do seu ambiente de trabalho.</p>
      </section>
      <section className="auth-card">
        <div className="access-session"><SessionControls label={session.user.name || session.user.email || "Usuário autenticado"} /></div>
        <div className="invitation-card">
          <span className="invitation-eyebrow">CONVITE DE ACESSO</span>
          <h1>Seu ambiente está quase pronto.</h1>
          <p>Confirme o convite para liberar seu acesso administrativo ao Beauty Coworking OS.</p>
          <div className="invitation-role"><span>PERFIL</span><strong>{invitation.role}</strong></div>
          <form action={acceptPendingInvitation}>
            <input type="hidden" name="membershipId" value={invitation.id} />
            <button type="submit">Aceitar convite e continuar</button>
          </form>
          <a className="invitation-back" href="/acesso">Voltar aos acessos</a>
        </div>
      </section>
    </main>
  );
}
