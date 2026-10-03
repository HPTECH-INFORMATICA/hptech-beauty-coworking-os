import Link from "next/link";

import { getTenantMembershipPermissions, getTenantMemberships, type TenantPermission } from "../../../lib/bcos-api";
import { inviteUserAction, removeUserAction, updateUserAction, updateUserPermissionsAction, updateUserStatusAction } from "./actions";

export const dynamic = "force-dynamic";

const roleLabel = { OWNER: "Proprietário", ADMIN: "Administrador", RECEPTION: "Recepção", PROFESSIONAL: "Profissional" } as const;
const statusLabel = { INVITED: "Convite pendente", ACTIVE: "Ativo", INACTIVE: "Bloqueado" } as const;
const permissionGroups: Array<{title:string; description:string; items:Array<{permission:TenantPermission; label:string}>}> = [
  { title:"Operação", description:"Acesso às telas usadas no dia a dia do coworking.", items:[
    {permission:"DASHBOARD_VIEW",label:"Visão geral"},
    {permission:"AGENDA_VIEW",label:"Visualizar agenda"},
    {permission:"AGENDA_MANAGE",label:"Criar e confirmar reservas"},
    {permission:"AVAILABILITY_VIEW",label:"Consultar disponibilidade"},
    {permission:"CHECKIN_MANAGE",label:"Realizar check-in e check-out"},
  ]},
  { title:"Financeiro", description:"Dados e ações financeiras do contratante.", items:[
    {permission:"FINANCE_VIEW",label:"Visualizar financeiro"},
    {permission:"FINANCE_MANAGE",label:"Fechar faturas e confirmar pagamentos"},
  ]},
  { title:"Administração", description:"Configuração e autoridade sobre o ambiente do cliente.", items:[
    {permission:"ADMIN_CONFIG",label:"Configurar empresa, unidades, espaços, horários, preços e profissionais"},
    {permission:"USER_ADMIN",label:"Administrar usuários, papéis, bloqueios e permissões"},
  ]},
  { title:"Portal profissional", description:"Área pessoal, sem acesso administrativo do contratante.", items:[
    {permission:"PROFESSIONAL_OWN",label:"Acessar somente o próprio portal profissional"},
  ]},
];

export default async function UsersAdminPage({ searchParams }: { searchParams: Promise<{ invited?: string }> }) {
  const [{ invited }, memberships] = await Promise.all([searchParams, getTenantMemberships()]);
  const permissionEntries = await Promise.all(memberships.map(async item => [item.id, await getTenantMembershipPermissions(item.id)] as const));
  const effectivePermissions = new Map(permissionEntries);

  return <main className="admin-page admin-users-page">
    <header className="admin-page-head">
      <div><span>Administração / Usuários</span><h1>Usuários, papéis e permissões</h1>
        <p>Defina quem entra no ambiente, quais telas cada pessoa pode acessar e quais ações pode executar.</p></div>
      <nav className="admin-section-nav" aria-label="Administração de usuários">
        <Link href="/administracao">Configurações</Link><Link className="active" href="/administracao/usuarios">Usuários</Link>
      </nav>
    </header>

    {invited ? <div className="platform-success"><strong>Convite registrado</strong><span>O acesso permanece pendente até a pessoa aceitar o vínculo pela própria conta.</span></div> : null}

    <section className="tenant-user-summary">
      <div><strong>{memberships.length}</strong><span>usuários cadastrados</span></div>
      <div><strong>{memberships.filter(x=>x.status==="ACTIVE").length}</strong><span>acessos ativos</span></div>
      <div><strong>{memberships.filter(x=>x.status==="INACTIVE").length}</strong><span>acessos bloqueados</span></div>
    </section>

    <section className="tenant-user-management">
      <div className="tenant-user-list">
        {memberships.map(item => {
          const owner=item.role==="OWNER";
          const displayName=item.display_name || (owner ? "Proprietário principal" : "Usuário sem nome cadastrado");
          const granted=new Set(effectivePermissions.get(item.id) ?? []);
          return <article key={item.id} className="tenant-user-card tenant-user-card-rich">
            <div className="tenant-user-identity">
              <span className="tenant-user-role">{roleLabel[item.role]}</span><strong>{displayName}</strong>
              <small>{item.email || "E-mail não informado"}</small>
            </div>
            <div className="tenant-user-state">
              <span className={`tenant-user-status status-${item.status.toLowerCase()}`}>{statusLabel[item.status]}</span>
              {owner ? <span className="tenant-owner-lock">Proprietário protegido</span> : null}
            </div>

            <div className="tenant-permission-overview">
              <strong>{owner ? "Acesso integral do proprietário" : "Acessos liberados"}</strong>
              <div className="tenant-user-permissions">{permissionGroups.flatMap(group=>group.items).filter(x=>granted.has(x.permission)).map(x=><span key={x.permission}>{x.label}</span>)}</div>
            </div>

            {owner ? <div className="tenant-user-owner-note"><strong>Conta principal do contratante</strong><span>Possui acesso integral. Não pode ser bloqueada, removida, rebaixada ou ter permissões retiradas por esta tela.</span></div> :
            <details className="tenant-user-editor">
              <summary>Editar usuário e acesso</summary>
              <form className="tenant-user-edit-form" action={updateUserAction}>
                <input type="hidden" name="membership_id" value={item.id}/>
                <label>Nome<input name="display_name" defaultValue={item.display_name ?? ""} required/></label>
                <div className="tenant-user-readonly"><span>E-mail de acesso</span><strong>{item.email || "Não disponível"}</strong><small>Identidade de autenticação do próprio usuário.</small></div>
                <label>Papel<select name="role" defaultValue={item.role}><option value="ADMIN">Administrador</option><option value="RECEPTION">Recepção</option><option value="PROFESSIONAL">Profissional</option></select></label>
                <button type="submit">Salvar dados e papel</button>
              </form>

              <form className="tenant-permission-editor" action={updateUserPermissionsAction}>
                <input type="hidden" name="membership_id" value={item.id}/>
                <div className="permission-editor-head"><strong>Permissões deste usuário</strong><span>Marque somente o que esta pessoa realmente pode acessar ou executar.</span></div>
                {permissionGroups.map(group=><fieldset key={group.title}><legend>{group.title}</legend><p>{group.description}</p>
                  {group.items.map(entry=><label className="permission-check" key={entry.permission}>
                    <input type="checkbox" name={entry.permission} defaultChecked={granted.has(entry.permission)}/><span>{entry.label}</span>
                  </label>)}
                </fieldset>)}
                <button type="submit">Salvar permissões</button>
              </form>

              <div className="tenant-user-access-actions">
                <form action={updateUserStatusAction}><input type="hidden" name="membership_id" value={item.id}/><input type="hidden" name="status" value={item.status==="ACTIVE"?"INACTIVE":"ACTIVE"}/><button type="submit">{item.status==="ACTIVE"?"Bloquear acesso":"Ativar acesso"}</button></form>
                <form action={removeUserAction}><input type="hidden" name="membership_id" value={item.id}/><button className="danger" type="submit">Remover acesso</button></form>
              </div>
            </details>}
          </article>;
        })}
      </div>

      <aside className="tenant-invite-card"><span>NOVO ACESSO</span><h2>Adicionar usuário da equipe</h2>
        <p>Cadastre a identidade e escolha o papel inicial. Após o convite, as permissões poderão ser ajustadas individualmente.</p>
        <form action={inviteUserAction}><label>Nome<input name="display_name" required placeholder="Nome completo"/></label>
          <label>E-mail<input name="email" type="email" required placeholder="usuario@empresa.com"/></label>
          <label>Papel<select name="role" defaultValue="RECEPTION"><option value="ADMIN">Administrador</option><option value="RECEPTION">Recepção</option><option value="PROFESSIONAL">Profissional</option></select></label>
          <button type="submit">Enviar convite</button></form>
        <div className="tenant-password-policy"><strong>Senha e segurança</strong><p>O BCOS não exibe nem redefine a senha de outro usuário. A credencial pertence à conta de autenticação da própria pessoa.</p></div>
      </aside>
    </section>
  </main>;
}
