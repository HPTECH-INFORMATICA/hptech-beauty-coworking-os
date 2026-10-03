import { notFound } from "next/navigation";
import { getPendingTeamInvitations } from "../../../../lib/bcos-api";
import { acceptTeamInvitationAction } from "./actions";

export const dynamic="force-dynamic";

export default async function TeamInvitationPage({params}:{params:Promise<{id:string}>}) {
  const {id}=await params;
  const invitation=(await getPendingTeamInvitations()).find(item=>item.id===id);
  if(!invitation) notFound();
  const role={ADMIN:"Administrador",RECEPTION:"Recepção",PROFESSIONAL:"Profissional"}[invitation.role];
  return <main className="auth-shell"><section className="auth-brand"><span>HPTECH PLATFORM</span><h1>Beauty Coworking OS</h1><p>Confirme o vínculo antes de acessar o ambiente.</p></section><section className="auth-card"><div className="invitation-review"><span>CONVITE DA EQUIPE</span><h2>{invitation.tenant_name}</h2><p><strong>{invitation.display_name}</strong><br/>{invitation.email}</p><div className="invitation-role"><small>Papel concedido</small><strong>{role}</strong></div><p>Ao aceitar, esta conta será vinculada ao negócio com as permissões correspondentes ao papel acima.</p><form action={acceptTeamInvitationAction}><input type="hidden" name="invitation_id" value={invitation.id}/><button type="submit">Aceitar acesso</button></form></div></section></main>;
}
