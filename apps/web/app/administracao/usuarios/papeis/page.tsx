import Link from "next/link";
import { requireTenantPermission } from "../../../../lib/auth/authorization";
import { getAccessRolePermissionCatalog, getAccessRoles } from "../../../../lib/bcos-api";
import { createRoleAction, deleteRoleAction, updateRoleAction } from "./actions";
export const dynamic="force-dynamic";

type Catalog = Awaited<ReturnType<typeof getAccessRolePermissionCatalog>>;

function Matrix({catalog,selected}:{catalog:Catalog;selected:Set<string>}){
 const modules=[...new Set(catalog.map(item=>item.module))];
 return <div className="role-capability-groups">
  {modules.map(module=>{
   const capabilities=catalog.filter(item=>item.module===module);
   return <fieldset className="role-capability-group" key={module}>
    <legend>{module}</legend>
    <div className="role-capability-options">{capabilities.map(item=><label className="role-capability-option" key={item.code}>
     <input aria-label={`${module}: ${item.action}`} type="checkbox" name={"permission:"+item.code} defaultChecked={selected.has(item.code)}/>
     <span><b>{item.action}</b><small>Permitir esta ação em {module.toLowerCase()}.</small></span>
    </label>)}</div>
   </fieldset>;
  })}
 </div>;
}

export default async function RolesPage(){
 await requireTenantPermission("ROLE_MANAGE");
 const [roles,catalog]=await Promise.all([getAccessRoles(),getAccessRolePermissionCatalog()]);
 return <main className="admin-page admin-users-page admin-roles-page">
  <header className="admin-page-head"><div><span>ADMINISTRAÇÃO / CONTROLE DE ACESSO</span><h1>Papéis e permissões</h1><p>Crie as funções da sua equipe e escolha somente as ações que cada papel poderá executar.</p></div><nav className="admin-section-nav admin-access-nav" aria-label="Navegação do controle de acesso">
<Link href="/administracao?area=empresa">Empresa</Link>
<Link href="/administracao?area=unidades">Unidades</Link>
<Link href="/administracao?area=espacos">Espaços</Link>
<Link href="/administracao?area=funcionamento">Funcionamento</Link>
<Link href="/administracao?area=precos">Preços</Link>
<Link href="/administracao?area=profissionais">Profissionais</Link>
<Link href="/administracao/usuarios">Usuários e acessos</Link>
<Link className="active" href="/administracao/usuarios/papeis">Papéis e permissões</Link>
</nav></header>
  <section className="role-governance-banner"><div><span>GOVERNANÇA DO AMBIENTE</span><strong>Seu negócio define os papéis da equipe</strong><p>A HPTECH PLATFORM protege a autoridade do proprietário e a segurança do ambiente. Os demais papéis e permissões operacionais pertencem ao contratante.</p></div><div className="role-governance-stats"><span><strong>{roles.length}</strong>Papéis</span><span><strong>{roles.filter(role=>role.active).length}</strong>Ativos</span><span><strong>{roles.reduce((total,role)=>total+role.assigned_users,0)}</strong>Vínculos</span></div></section>
  <section className="role-directory"><div className="tenant-section-title"><div><span>PAPÉIS CADASTRADOS</span><h2>Estrutura de acesso</h2><p>Abra um papel para revisar seus dados e a matriz completa de permissões.</p></div></div>
   {roles.length===0?<div className="role-empty"><div><strong>Nenhum papel cadastrado</strong><p>Abra “Adicionar papel” abaixo para cadastrar a primeira função da equipe.</p></div></div>:<div className="role-list">{roles.map(role=><details className="role-record" key={role.id}><summary><div><strong>{role.name}</strong><small>{role.description||"Sem descrição"}</small></div><div className="role-record-meta"><span>{role.assigned_users} usuário(s)</span><span className={role.active?"status-active":"status-inactive"}>{role.active?"Ativo":"Inativo"}</span><b>Editar</b></div></summary>
    <form className="role-editor" action={updateRoleAction}><input type="hidden" name="role_id" value={role.id}/>
     <div className="role-editor-heading"><div><span>EDITAR PAPEL</span><h3>{role.name}</h3><p>Atualize a identidade do papel e suas autorizações. Alterações afetam os usuários vinculados a esta função.</p></div><label className="role-active-toggle"><input type="checkbox" name="active" defaultChecked={role.active}/><span>Papel ativo</span></label></div>
     <div className="role-identity-grid"><label>Nome<input name="name" defaultValue={role.name} required/></label><label>Descrição<input name="description" defaultValue={role.description??""} placeholder="Responsabilidade deste papel"/></label></div>
     <div className="role-matrix-section"><div><span>PERMISSÕES DO PAPEL</span><strong>O que esta função pode fazer</strong><p>Escolha as ações permitidas em cada área. O sistema mostra apenas ações que realmente existem naquela área.</p></div><Matrix catalog={catalog} selected={new Set(role.permissions)}/></div>
     <div className="role-editor-footer"><div><strong>Remoção protegida</strong><span>Papéis vinculados a usuários precisam ser reatribuídos antes da remoção.</span></div><div><button formAction={deleteRoleAction} className="role-secondary-danger" type="submit">Remover papel</button><button type="submit">Salvar alterações</button></div></div>
    </form></details>)}</div>}
  </section>
  <details className="admin-editor role-create-editor"><summary>Adicionar papel</summary><form className="role-create-card role-create-form" action={createRoleAction}><div className="role-create-heading"><span>NOVO PAPEL</span><h2>Cadastrar papel</h2><p>Defina a função e escolha as permissões que pertencem a este papel.</p></div><div className="role-identity-grid"><label>Nome<input name="name" required placeholder="Ex.: Gerente, Caixa, Recepção"/></label><label>Descrição<input name="description" placeholder="Responsabilidade deste papel"/></label></div><div className="role-matrix-section"><div><span>PERMISSÕES DO NOVO PAPEL</span><strong>Escolha o que esta função poderá fazer</strong><p>Marque as ações desejadas por área. Você poderá alterar essas permissões depois.</p></div><Matrix catalog={catalog} selected={new Set()}/></div><div className="role-create-actions"><button type="submit">Cadastrar papel</button></div></form></details>
 </main>;
}
