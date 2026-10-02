import { redirect } from "next/navigation";
import { getPendingProfessionalInvitations } from "../../../../lib/bcos-api";
import { auth } from "../../../../lib/auth/server";
import { SessionControls } from "../../../../components/session-controls";
import { acceptProfessionalAccess } from "./actions";

export const dynamic = "force-dynamic";

export default async function ProfessionalInvitationPage({ params }: { params: Promise<{ id: string }> }) {
  const { data: session } = await auth.getSession();
  if (!session?.user) redirect("/auth/sign-in");
  const { id } = await params;
  const invitations = await getPendingProfessionalInvitations();
  const invitation = invitations.find((item) => item.id === id);
  if (!invitation) redirect("/acesso");

  return <main className="auth-shell">
    <section className="auth-brand">
      <span>HPTECH PLATFORM</span>
      <h1>Beauty Coworking OS</h1>
      <p>Seu acesso profissional é pessoal e vinculado à unidade que fez o convite.</p>
    </section>
    <section className="auth-card">
      <div className="access-session"><SessionControls label={session.user.name || session.user.email || "Profissional autenticado"} /></div>
      <div className="invitation-card">
        <span className="invitation-eyebrow">CONVITE PROFISSIONAL</span>
        <h1>Confirme seu vínculo profissional.</h1>
        <p>A unidade <strong>{invitation.tenant_name}</strong> preparou acesso ao Portal do Profissional para <strong>{invitation.professional_name}</strong>.</p>
        <div className="invitation-role"><span>PERFIL</span><strong>Profissional</strong></div>
        <p>Ao aceitar, esta conta será vinculada ao seu cadastro profissional nessa empresa. O acesso continuará limitado às permissões do perfil Profissional.</p>
        <form action={acceptProfessionalAccess}>
          <input type="hidden" name="invitationId" value={invitation.id}/>
          <button type="submit">Aceitar e abrir meu portal</button>
        </form>
        <a className="invitation-back" href="/acesso">Voltar aos acessos</a>
      </div>
    </section>
  </main>;
}
