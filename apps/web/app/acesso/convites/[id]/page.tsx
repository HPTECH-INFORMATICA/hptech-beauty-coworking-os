import { redirect } from "next/navigation";

import { getPendingInvitations } from "../../../../lib/bcos-api";
import { auth } from "../../../../lib/auth/server";
import { acceptPendingInvitation } from "../actions";

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
      <section className="auth-card">
        <h1>Aceitar convite</h1>
        <p>Perfil: {invitation.role}</p>
        <form action={acceptPendingInvitation}>
          <input type="hidden" name="membershipId" value={invitation.id} />
          <button type="submit">Aceitar e continuar</button>
        </form>
      </section>
    </main>
  );
}
