import { requireTenantPermission } from "../../../lib/auth/authorization";
import Link from "next/link";

import { getTenantMembershipPermissions, getTenantMemberships, type TenantPermission } from "../../../lib/bcos-api";
import { inviteUserAction, removeUserAction, updateUserAction, updateUserPermissionsAction, updateUserStatusAction } from "./actions";

export const dynamic = "force-dynamic";

const roleLabel = { OWNER:"Proprietário", ADMIN:"Administrador", RECEPTION:"Recepção", PROFESSIONAL:"Profissional" } as const;
const statusLabel = { INVITED:"Convite pendente", ACTIVE:"Ativo", INACTIVE:"Bloqueado" } as const;
const permissionGroups:Array<{title:string;items:Array<{permission:TenantPermission;label:string}>}>=[
 {title:"Operação",items:[{permission:"DASHBOARD_VIEW",label:"Visão geral"},{permission:"AGENDA_VIEW",label:"Visualizar agenda"},{permission:"AGENDA_MANAGE",label:"Criar e confirmar reservas"},{permission:"AVAILABILITY_VIEW",label:"Consultar disponibilidade"},{permission:"CHECKIN_MANAGE",label:"Check-in e check-out"}]},
 {title:"Financeiro",items:[{permission:"FINANCE_VIEW",label:"Visualizar financeiro"},{permission:"FINANCE_MANAGE",label:"Fechar faturas e confirmar pagamentos"}]},
 {title:"Administração",items:[{permission:"ADMIN_CONFIG",label:"Configurar o ambiente"},{permission:"USER_ADMIN",label:"Administrar usuários e permissões"}]},
 {title:"Portal profissional",items:[{permission:"PROFESSIONAL_OWN",label:"Acessar o próprio portal profissional"}]},
];

export default async function UsersAdminPage({searchParams}:{searchParams:Promise<{invited?:string}>}){
 await requireTenantPermission("USER_ADMIN");
 const [{invited},memberships]=await Promise.all([searchParams,getTenantMemberships()]);
 const entries=await Promise.all(memberships.map(async item=>[item.id,await getTenantMembershipPermissions(item.id)] as const));
 const effective=new Map(entries);
 const manageableMemberships=memberships.filter(item=>item.role!=="OWNER");
 return <main className="admin-page admin-users-page">
  <header className="admin-page-head"><div><span>ADMINISTRAÇÃO / USUÁRIOS</span><h1>Usuários e acessos</h1><p>Cadastre a equipe, defina o papel e controle exatamente o que cada usuário pode acessar.</p></div>
   <nav className="admin-section-nav" aria-label="Navegação da administração"><Link href="/administracao">← Configurações</Link></nav></header>
  {invited?<div className="platform-success"><strong>Convite enviado</strong><span>O acesso ficará pendente até a pessoa aceitar o vínculo.</span></div>:null}
  <section className="tenant-user-summary"><div><strong>{memberships.length}</strong><span>Usuários</span></div><div><strong>{memberships.filter(x=>x.status==="ACTIVE").length}</strong><span>Ativos</span></div><div><strong>{memberships.filter(x=>x.status==="INACTIVE").length}</strong><span>Bloqueados</span></div></section>
  <section className="tenant-user-workspace">
   <section className="tenant-user-directory"><div className="tenant-section-title"><div><span>GESTÃO DE ACESSOS</span><h2>Gerenciador de acessos</h2></div><small>Você, como proprietário, administra os papéis, telas, permissões, bloqueios e remoções dos usuários da equipe.</small></div>
    <div className="tenant-access-manager-intro"><div><strong>Você administra os acessos da equipe</strong><p>O proprietário mantém acesso integral protegido e define o acesso de cada pessoa da equipe.</p></div></div>
    <div className="tenant-access-guide" aria-label="Como funciona o controle de acesso">
     <div><strong>1. Papel</strong><p>Função inicial do usuário: Administrador, Recepção ou Profissional. O papel aplica uma base de permissões.</p></div>
     <div><strong>2. Telas e ações</strong><p>Depois do convite, abra “Gerenciar acesso” para escolher exatamente quais áreas pode visualizar e quais ações pode executar.</p></div>
     <div><strong>3. Bloquear acesso</strong><p>Suspende temporariamente a entrada deste usuário no ambiente. O cadastro e o histórico permanecem.</p></div>
     <div><strong>4. Remover acesso</strong><p>Encerra o vínculo deste usuário com este ambiente. Não exclui a conta de autenticação da pessoa.</p></div>
    </div>{manageableMemberships.length===0?<div className="tenant-access-empty"><div><strong>Ainda não há usuários da equipe</strong><p>O gerenciador já está disponível para você. Adicione o primeiro usuário para configurar o acesso individual.</p></div><a href="#adicionar-usuario">Adicionar usuário</a></div>:null}
    <div className="tenant-user-list">{memberships.map(item=>{const owner=item.role==="OWNER",granted=new Set(effective.get(item.id)??[]),name=item.display_name||(owner?"Proprietário principal":"Usuário sem nome");
     return <article key={item.id} className="tenant-user-card tenant-user-card-professional">
      <div className="tenant-user-row">
       <div className="tenant-user-avatar">{name.slice(0,1).toUpperCase()}</div>
       <div className="tenant-user-identity"><strong>{name}</strong><small>{item.email||"E-mail não informado"}</small></div>
       <div className="tenant-user-meta"><span>{roleLabel[item.role]}</span><span className={`tenant-user-status status-${item.status.toLowerCase()}`}>{statusLabel[item.status]}</span></div>
       <div className="tenant-user-row-actions">{owner?<span className="tenant-owner-lock">Acesso integral protegido</span>:<span className="tenant-manage-hint">Editar • Permissões • Bloquear • Remover ↓</span>}</div>
      </div>
      {owner?<div className="tenant-owner-access"><strong>Proprietário do ambiente</strong><p>Possui acesso integral a todos os módulos e ações. Este acesso não pode ser rebaixado, bloqueado ou removido.</p></div>:
       <details className="tenant-user-editor tenant-user-editor-professional"><summary>Gerenciar acesso</summary><div className="tenant-access-console">
        <section className="tenant-access-panel"><div className="tenant-panel-head"><span>01</span><div><strong>Dados e papel</strong><small>Identificação do usuário e função principal.</small></div></div>
         <form className="tenant-user-edit-form tenant-user-edit-stacked" action={updateUserAction}><input type="hidden" name="membership_id" value={item.id}/>
          <label>Nome<input name="display_name" defaultValue={item.display_name??""} required/></label>
          <div className="tenant-user-readonly"><span>E-mail de acesso</span><strong>{item.email||"Não disponível"}</strong><small>O e-mail de autenticação não é alterado pelo contratante.</small></div>
          <label>Papel<select name="role" defaultValue={item.role}><option value="ADMIN">Administrador</option><option value="RECEPTION">Recepção</option><option value="PROFESSIONAL">Profissional</option></select></label>
          <button type="submit">Salvar dados e papel</button></form></section>
        <section className="tenant-access-panel tenant-access-panel-wide"><div className="tenant-panel-head"><span>02</span><div><strong>Telas e ações permitidas</strong><small>Defina o que este usuário pode ver e o que pode fazer em cada área.</small></div></div>
         <form className="tenant-permission-editor tenant-permission-matrix" action={updateUserPermissionsAction}><input type="hidden" name="membership_id" value={item.id}/>
          {permissionGroups.map(group=><fieldset key={group.title}><legend>{group.title}</legend>{group.items.map(entry=><label className="permission-check" key={entry.permission}><input type="checkbox" name={entry.permission} defaultChecked={granted.has(entry.permission)}/><span>{entry.label}</span></label>)}</fieldset>)}
          <button type="submit">Salvar permissões</button></form></section>
        <section className="tenant-access-panel tenant-danger-panel"><div className="tenant-panel-head"><span>03</span><div><strong>Bloqueio e remoção</strong><small>Bloquear suspende o acesso; remover encerra o vínculo com este ambiente.</small></div></div>
         <div className="tenant-user-access-actions"><form action={updateUserStatusAction}><input type="hidden" name="membership_id" value={item.id}/><input type="hidden" name="status" value={item.status==="ACTIVE"?"INACTIVE":"ACTIVE"}/><button type="submit">{item.status==="ACTIVE"?"Bloquear acesso":"Reativar acesso"}</button></form>
          <form action={removeUserAction}><input type="hidden" name="membership_id" value={item.id}/><button className="danger" type="submit">Remover acesso</button></form></div></section>
       </div></details>}
     </article>})}</div>
   </section>
   <aside id="adicionar-usuario" className="tenant-invite-card tenant-invite-card-sticky"><span>NOVO USUÁRIO</span><h2>Adicionar à equipe</h2><p>Informe os dados e o papel inicial. Depois você poderá personalizar as permissões.</p>
    <form action={inviteUserAction}><label>Nome<input name="display_name" required placeholder="Nome completo"/></label><label>E-mail<input name="email" type="email" required placeholder="usuario@empresa.com"/></label><label>Papel<select name="role" defaultValue="RECEPTION"><option value="ADMIN">Administrador</option><option value="RECEPTION">Recepção</option><option value="PROFESSIONAL">Profissional</option></select></label><button type="submit">Enviar convite</button></form>
    <div className="tenant-password-policy"><strong>Senha protegida</strong><p>A senha pertence à conta de autenticação do próprio usuário e nunca é exibida nesta administração.</p></div>
   </aside>
  </section>
 </main>;
}
