import Link from "next/link";
import { requireTenantPermission } from "../../../../lib/auth/authorization";
import { getAccessRolePermissionCatalog, getAccessRoles } from "../../../../lib/bcos-api";
import { createRoleAction, deleteRoleAction, updateRoleAction } from "./actions";
export const dynamic="force-dynamic";

type Catalog = Awaited<ReturnType<typeof getAccessRolePermissionCatalog>>;

function Matrix({catalog,selected}:{catalog:Catalog;selected:Set<string>}){
 const modules=[...new Set(catalog.map(item=>item.module))];
 const actions=[...new Set(catalog.map(item=>item.action))];
 return <div className="role-permission-matrix">
  <div className="role-matrix-row role-matrix-head"><strong>Módulo</strong>{actions.map(action=><strong key={action}>{action}</strong>)}</div>
  {modules.map(module=><div className="role-matrix-row" key={module}><strong>{module}</strong>{actions.map(action=>{const item=catalog.find(entry=>entry.module===module&&entry.action===action);return <label key={action} className={!item?"role-matrix-unavailable":""}>{item?<><input aria-label={`${module}: ${action}`} type="checkbox" name={"permission:"+item.code} defaultChecked={selected.has(item.code)}/><span aria-hidden="true">✓</span></>:<span>—</span>}</label>})}</div>)}
 </div>;
}

export default async function RolesPage(){
 await requireTenantPermission("ROLE_MANAGE");
 const [roles,catalog]=await Promise.all([getAccessRoles(),getAccessRolePermissionCatalog()]);
 return <main className="admin-page admin-users-page admin-roles-page">
  <header className="admin-page-head"><div><span>ADMINISTRAÇÃO / CONTROLE DE ACESSO</span><h1>Papéis e permissões</h1><p>Crie funções da sua operação e defina, em uma matriz única, exatamente o que cada papel pode acessar e executar.</p></div><nav className="admin-section-nav" aria-label="Navegação do controle de acesso"><Link href="/administracao/usuarios">Usuários e acessos</Link><a href="#novo-papel">+ Novo papel</a></nav></header>
  <section className="role-governance-banner"><div><span>GOVERNANÇA DO AMBIENTE</span><strong>Seu negócio define os papéis da equipe</strong><p>A HPTECH PLATFORM protege a autoridade do proprietário e a segurança do ambiente. Os demais papéis e permissões operacionais pertencem ao contratante.</p></div><div className="role-governance-stats"><span><strong>{roles.length}</strong>Papéis</span><span><strong>{roles.filter(role=>role.active).length}</strong>Ativos</span><span><strong>{roles.reduce((total,role)=>total+role.assigned_users,0)}</strong>Vínculos</span></div></section>
  <section className="role-directory"><div className="tenant-section-title"><div><span>PAPÉIS CADASTRADOS</span><h2>Estrutura de acesso</h2><p>Abra um papel para revisar seus dados e a matriz completa de permissões.</p></div></div>
   {roles.length===0?<div className="role-empty"><div><strong>Nenhum papel cadastrado</strong><p>Crie o primeiro papel para começar a organizar os acessos da equipe.</p></div><a href="#novo-papel">Criar primeiro papel</a></div>:<div className="role-list">{roles.map(role=><details className="role-record" key={role.id}><summary><div><strong>{role.name}</strong><small>{role.description||"Sem descrição"}</small></div><div className="role-record-meta"><span>{role.assigned_users} usuário(s)</span><span className={role.active?"status-active":"status-inactive"}>{role.active?"Ativo":"Inativo"}</span><b>Editar</b></div></summary>
    <form className="role-editor" action={updateRoleAction}><input type="hidden" name="role_id" value={role.id}/>
     <div className="role-editor-heading"><div><span>EDITAR PAPEL</span><h3>{role.name}</h3><p>Atualize a identidade do papel e suas autorizações. Alterações afetam os usuários vinculados a esta função.</p></div><label className="role-active-toggle"><input type="checkbox" name="active" defaultChecked={role.active}/><span>Papel ativo</span></label></div>
     <div className="role-identity-grid"><label>Nome<input name="name" defaultValue={role.name} required/></label><label>Descrição<input name="description" defaultValue={role.description??""} placeholder="Responsabilidade deste papel"/></label></div>
     <div className="role-matrix-section"><div><span>MATRIZ DE ACESSO</span><strong>Permissões por módulo e ação</strong><p>Marque somente o necessário para esta função.</p></div><Matrix catalog={catalog} selected={new Set(role.permissions)}/></div>
     <div className="role-editor-footer"><div><strong>Remoção protegida</strong><span>Papéis vinculados a usuários precisam ser reatribuídos antes da remoção.</span></div><div><button formAction={deleteRoleAction} className="role-secondary-danger" type="submit">Remover papel</button><button type="submit">Salvar alterações</button></div></div>
    </form></details>)}</div>}
  </section>
  <section id="novo-papel" className="role-create-card"><div className="role-create-heading"><span>NOVO PAPEL</span><h2>Cadastrar papel</h2><p>Defina a função e configure toda a matriz sem sair desta área de trabalho.</p></div><form action={createRoleAction}><div className="role-identity-grid"><label>Nome<input name="name" required placeholder="Ex.: Gerente, Caixa, Recepção"/></label><label>Descrição<input name="description" placeholder="Responsabilidade deste papel"/></label></div><div className="role-matrix-section"><div><span>MATRIZ INICIAL</span><strong>Permissões do novo papel</strong><p>Você poderá ajustar esta matriz depois.</p></div><Matrix catalog={catalog} selected={new Set()}/></div><div className="role-create-actions"><Link href="/administracao/usuarios">Cancelar</Link><button type="submit">Cadastrar papel</button></div></form></section>
 </main>;
}
