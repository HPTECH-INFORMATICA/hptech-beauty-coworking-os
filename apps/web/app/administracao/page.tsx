import Link from "next/link";

import {
  getPricingRules,
  getProfessionals,
  getResourceCategories,
  getResources,
  getUnits,
} from "../../lib/bcos-api";
import {
  createCategoryAction,
  createProfessionalAction,
  createResourceAction,
  createUnitAction,
} from "./actions";

export const dynamic = "force-dynamic";

export default async function TenantAdministrationPage() {
  const [units, categories, resources, professionals, pricingRules] = await Promise.all([
    getUnits(),
    getResourceCategories(),
    getResources(),
    getProfessionals(),
    getPricingRules(),
  ]);

  return <main className="tenant-admin-shell">
    <aside className="tenant-admin-rail"><div><div className="platform-brand"><span>C</span><div><strong>BCOS</strong><small>Administração do Coworking</small></div></div><nav><Link className="active" href="/administracao">Cadastros</Link><Link href="/administracao/usuarios">Usuários</Link></nav></div><div className="platform-rail-foot"><small>ÁREA DO CONTRATANTE</small><strong>Gestão do seu coworking</strong></div></aside>
    <section className="platform-workspace"><header className="platform-header"><div><span>ADMINISTRAÇÃO / CADASTROS</span><strong>Estrutura operacional</strong></div><Link href="/">Ir para operação</Link></header>
      <div className="platform-canvas"><div className="platform-title"><span>C2 — TENANT MASTER DATA</span><h1>Configure o coworking.</h1><p>Unidades, categorias, recursos e profissionais usam os contratos já congelados no backend.</p></div>
        <section className="tenant-user-layout"><div className="tenant-user-list">
          <article className="tenant-user-card"><div><span>UNIDADES</span><strong>{units.length} cadastrada(s)</strong><small>{units.map(x=>x.name).join(" · ") || "Nenhuma unidade"}</small></div><form action={createUnitAction}><input name="name" required placeholder="Nome da unidade"/><input name="timezone" defaultValue="America/Sao_Paulo" required/><button type="submit">Adicionar</button></form></article>
          <article className="tenant-user-card"><div><span>CATEGORIAS</span><strong>{categories.length} cadastrada(s)</strong><small>{categories.map(x=>x.name).join(" · ") || "Nenhuma categoria"}</small></div><form action={createCategoryAction}><input name="name" required placeholder="Ex.: Sala de estética"/><button type="submit">Adicionar</button></form></article>
          <article className="tenant-user-card"><div><span>RECURSOS</span><strong>{resources.length} cadastrado(s)</strong><small>{resources.map(x=>x.name).join(" · ") || "Nenhum recurso"}</small></div><form action={createResourceAction}><input name="name" required placeholder="Nome do recurso"/><select name="unit_id" required defaultValue=""><option value="" disabled>Unidade</option>{units.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select><select name="category_id" required defaultValue=""><option value="" disabled>Categoria</option>{categories.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select><button type="submit">Adicionar</button></form></article>
          <article className="tenant-user-card"><div><span>PROFISSIONAIS</span><strong>{professionals.length} cadastrado(s)</strong><small>{professionals.map(x=>x.name).join(" · ") || "Nenhum profissional"}</small></div><form action={createProfessionalAction}><input name="name" required placeholder="Nome"/><input name="email" type="email" placeholder="E-mail"/><input name="phone" placeholder="Telefone"/><button type="submit">Adicionar</button></form></article>
        </div><aside className="tenant-invite-card"><span>PRICING</span><h2>{pricingRules.length} regra(s) cadastrada(s)</h2><p>O motor e as regras permanecem separados dos cadastros operacionais. A administração completa de Pricing continua no gate C3.</p>{pricingRules.map(rule=><div key={rule.id}><strong>{rule.name}</strong><small>{rule.status} · prioridade {rule.priority}</small></div>)}</aside></section>
      </div>
    </section>
  </main>;
}
