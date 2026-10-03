import Link from "next/link";

import { getTenantMemberships, getTenantProfile } from "../../../lib/bcos-api";
import { inviteUserAction, removeUserAction, updateUserAction, updateUserStatusAction } from "./actions";

export const dynamic = "force-dynamic";

const roleLabel = { OWNER: "Proprietário", ADMIN: "Administrador", RECEPTION: "Recepção", PROFESSIONAL: "Profissional" } as const;
const statusLabel = { INVITED: "Convite pendente", ACTIVE: "Ativo", INACTIVE: "Bloqueado" } as const;
const permissions = {
  OWNER: ["Administração", "Operação"],
  ADMIN: ["Administração", "Operação"],
  RECEPTION: ["Operação"],
  PROFESSIONAL: ["Portal do profissional"],
} as const;

export default async function UsersAdminPage({ searchParams }: { searchParams: Promise<{ invited?: string }> }) {
  const [{ invited }, memberships, profile] = await Promise.all([searchParams, getTenantMemberships(), getTenantProfile()]);

  return <main className="admin-page admin-users-page">
    <header className="admin-page-head">
      <div>
        <span>Administração / Usuários</span>
        <h1>Usuários e acessos</h1>
        <p>Controle quem acessa a operação, o papel de cada pessoa e as permissões concedidas.</p>
      </div>
      <nav className="admin-section-nav" aria-label="Administração de usuários">
        <Link href="/administracao">Configurações</Link>
        <Link className="active" href="/administracao/usuarios">Usuários</Link>
      </nav>
    </header>

    {invited ? <div className="platform-success"><strong>Convite registrado</strong><span>O acesso permanece pendente até a identidade confiável ser ativada.</span></div> : null}

    <section className="tenant-user-summary">
      <div><strong>{memberships.length}</strong><span>usuários cadastrados</span></div>
      <div><strong>{memberships.filter(x=>x.status==="ACTIVE").length}</strong><span>acessos ativos</span></div>
      <div><strong>{memberships.filter(x=>x.status==="INACTIVE").length}</strong><span>acessos bloqueados</span></div>
    </section>

    <section className="tenant-user-management">
      <div className="tenant-user-list">
        {memberships.map((item) => {
          const owner=item.role==="OWNER";
          const displayName=item.display_name || (owner ? profile.trade_name : null) || "Usuário sem nome cadastrado";
          const email=item.email || (owner ? profile.email : null);
          return <article key={item.id} className="tenant-user-card tenant-user-card-rich">
            <div className="tenant-user-identity">
              <span className="tenant-user-role">{roleLabel[item.role]}</span>
              <strong>{displayName}</strong>
              <small>{email || "E-mail não informado"}</small>
              <div className="tenant-user-permissions">{permissions[item.role].map(p=><span key={p}>{p}</span>)}</div>
            </div>
            <div className="tenant-user-state">
              <span className={`tenant-user-status status-${item.status.toLowerCase()}`}>{statusLabel[item.status]}</span>
              {owner ? <span className="tenant-owner-lock">Acesso do proprietário protegido</span> : null}
            </div>
            {!owner ? <details className="tenant-user-editor">
              <summary>Gerenciar usuário</summary>
              <form className="tenant-user-edit-form" action={updateUserAction}>
                <input type="hidden" name="membership_id" value={item.id}/>
                <label>Nome<input name="display_name" defaultValue={item.display_name ?? ""} required placeholder="Nome do usuário"/></label>
                <label>E-mail<input name="email" type="email" defaultValue={item.email ?? ""} placeholder="usuario@empresa.com"/></label>
                <label>Papel<select name="role" defaultValue={item.role}><option value="ADMIN">Administrador</option><option value="RECEPTION">Recepção</option><option value="PROFESSIONAL">Profissional</option></select></label>
                <div className="tenant-user-actions"><button type="submit">Salvar alterações</button></div>
              </form>
              <div className="tenant-user-access-actions">
                <form action={updateUserStatusAction}><input type="hidden" name="membership_id" value={item.id}/><input type="hidden" name="status" value={item.status==="ACTIVE"?"INACTIVE":"ACTIVE"}/><button type="submit">{item.status==="ACTIVE"?"Bloquear acesso":"Ativar acesso"}</button></form>
                <form action={removeUserAction}><input type="hidden" name="membership_id" value={item.id}/><button className="danger" type="submit">Remover acesso</button></form>
              </div>
            </details> : <div className="tenant-user-owner-note"><strong>Conta principal do contratante</strong><span>O proprietário não pode ser bloqueado, removido ou rebaixado por esta tela.</span></div>}
            <details className="tenant-user-technical"><summary>Identificador técnico</summary><code>{item.external_user_id}</code></details>
          </article>;
        })}
        {!memberships.length ? <div className="access-empty"><strong>Nenhum usuário cadastrado</strong><span>Convide a equipe quando estiver pronta para operar o coworking.</span></div> : null}
      </div>

      <aside className="tenant-invite-card">
        <span>NOVO ACESSO</span>
        <h2>Adicionar usuário da equipe</h2>
        <p>O convite por e-mail será a entrada padrão. Enquanto a identidade de equipe não estiver vinculada, não compartilhe IDs técnicos manualmente.</p>
        <form action={inviteUserAction}>
          <label>Identificador da identidade<input name="external_user_id" required placeholder="Vínculo técnico temporário"/></label>
          <label>Papel<select name="role" defaultValue="RECEPTION"><option value="ADMIN">Administrador</option><option value="RECEPTION">Recepção</option><option value="PROFESSIONAL">Profissional</option></select></label>
          <button type="submit">Registrar acesso</button>
        </form>
        <div className="tenant-password-policy"><strong>Senha e segurança</strong><p>Senhas não são exibidas nem alteradas pelo contratante. Cada usuário gerencia a própria credencial pelo provedor seguro de autenticação.</p><Link href="/auth/sign-in">Ir para autenticação</Link></div>
      </aside>
    </section>
  </main>;
}
