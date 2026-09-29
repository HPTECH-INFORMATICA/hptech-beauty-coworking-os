import Link from "next/link";

import {
  getPricingRules,
  getReceptionHours,
  getTenantProfile,
  getProfessionals,
  getResourceCategories,
  getResources,
  getUnits,
} from "../../lib/bcos-api";
import {
  createCategoryAction,
  createPricingRuleAction,
  createProfessionalAction,
  createResourceAction,
  createUnitAction,
  updateReceptionHoursAction,
  updateTenantProfileAction,
} from "./actions";

export const dynamic = "force-dynamic";

export default async function TenantAdministrationPage() {
  const [units, categories, resources, professionals, pricingRules, profile] = await Promise.all([
    getUnits(),
    getResourceCategories(),
    getResources(),
    getProfessionals(),
    getPricingRules(),
    getTenantProfile(),
  ]);
  const receptionHoursByUnit = new Map(await Promise.all(units.map(async (unit) => [unit.id, await getReceptionHours(unit.id)] as const)));
  const dayNames = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"];

  return <main className="admin-page">
    <header className="admin-page-head">
      <div><span>Administração</span><h1>Configurações do coworking</h1><p>Organize os dados da empresa e a estrutura usada na operação diária.</p></div>
      <nav className="admin-section-nav" aria-label="Administração">
        <a href="#empresa">Empresa</a><a href="#unidades">Unidades</a><a href="#espacos">Espaços</a><a href="#profissionais">Profissionais</a><a href="#precos">Preços</a><Link href="/administracao/usuarios">Usuários</Link>
      </nav>
    </header>
    <section className="admin-settings-grid">
      <div className="tenant-user-list">
        <article id="empresa" className="tenant-user-card"><div><span>EMPRESA</span><strong>{profile.trade_name}</strong><small>{profile.legal_name}</small></div><form action={updateTenantProfileAction}><input name="trade_name" defaultValue={profile.trade_name} required placeholder="Nome fantasia"/><input name="legal_name" defaultValue={profile.legal_name} required placeholder="Razão social"/><input name="tax_id" defaultValue={profile.tax_id ?? ""} placeholder="CNPJ/CPF"/><input name="email" type="email" defaultValue={profile.email} required/><input name="phone" defaultValue={profile.phone ?? ""} placeholder="Telefone"/><button type="submit">Salvar empresa</button></form></article>
        <article id="unidades" className="tenant-user-card"><div><span>UNIDADES</span><strong>{units.length} cadastrada(s)</strong><small>{units.map(x=>x.name).join(" · ") || "Nenhuma unidade"}</small></div><form action={createUnitAction}><input name="name" required placeholder="Nome da unidade"/><input name="timezone" defaultValue="America/Sao_Paulo" required/><button type="submit">Adicionar unidade</button></form></article>
        {units.map((unit) => { const hoursByDay = new Map((receptionHoursByUnit.get(unit.id) ?? []).map((item) => [item.day_of_week, item])); return <article key={unit.id} className="tenant-user-card"><div><span>HORÁRIOS DE ATENDIMENTO</span><strong>{unit.name}</strong><small>Defina os horários disponíveis para a operação desta unidade.</small></div><form className="reception-hours-form" action={updateReceptionHoursAction}><input type="hidden" name="unit_id" value={unit.id}/>{dayNames.map((name, day) => { const item=hoursByDay.get(day); return <div key={day}><strong>{name}</strong><input name={`opens_${day}`} type="time" defaultValue={item?.opens_at?.slice(0,5) ?? "08:00"}/><input name={`closes_${day}`} type="time" defaultValue={item?.closes_at?.slice(0,5) ?? "18:00"}/><label><input name={`closed_${day}`} type="checkbox" defaultChecked={item?.is_closed ?? false}/> Fechado</label></div>;})}<button type="submit">Salvar horários de {unit.name}</button></form></article>; })}
        <article id="espacos" className="tenant-user-card"><div><span>CATEGORIAS DE ESPAÇOS</span><strong>{categories.length} cadastrada(s)</strong><small>{categories.map(x=>x.name).join(" · ") || "Nenhuma categoria"}</small></div><form action={createCategoryAction}><input name="name" required placeholder="Ex.: Sala de estética"/><button type="submit">Adicionar categoria</button></form></article>
        <article className="tenant-user-card"><div><span>ESPAÇOS E RECURSOS</span><strong>{resources.length} cadastrado(s)</strong><small>{resources.map(x=>x.name).join(" · ") || "Nenhum espaço cadastrado"}</small></div><form action={createResourceAction}><input name="name" required placeholder="Nome do espaço"/><select name="unit_id" required defaultValue=""><option value="" disabled>Unidade</option>{units.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select><select name="category_id" required defaultValue=""><option value="" disabled>Categoria</option>{categories.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select><button type="submit">Adicionar espaço</button></form></article>
        <article id="profissionais" className="tenant-user-card"><div><span>PROFISSIONAIS</span><strong>{professionals.length} cadastrado(s)</strong><small>{professionals.map(x=>x.name).join(" · ") || "Nenhum profissional"}</small></div><form action={createProfessionalAction}><input name="name" required placeholder="Nome"/><input name="email" type="email" placeholder="E-mail"/><input name="phone" placeholder="Telefone"/><button type="submit">Adicionar profissional</button></form></article>
      </div>
      <aside id="precos" className="tenant-invite-card"><span>PREÇOS E REGRAS</span><h2>{pricingRules.length} regra(s) cadastrada(s)</h2><p>Defina as regras comerciais aplicadas às reservas e aos espaços do coworking.</p>{pricingRules.map(rule=><div key={rule.id}><strong>{rule.name}</strong><small>{rule.status} · prioridade {rule.priority}</small></div>)}<form action={createPricingRuleAction}><input name="name" required placeholder="Nome da regra"/><select name="unit_id" defaultValue=""><option value="">Todas as unidades</option>{units.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select><select name="category_id" defaultValue=""><option value="">Todas as categorias</option>{categories.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select><input name="priority" type="number" min="0" defaultValue="100" required/><textarea name="rule_definition" required defaultValue="{}" aria-label="Definição da regra"/><input name="valid_from" type="datetime-local"/><input name="valid_until" type="datetime-local"/><button type="submit">Criar regra de preço</button></form></aside>
    </section>
  </main>;
}
