import Link from "next/link";

import {
  getPricingRules, getReceptionHours, getTenantProfile, getProfessionals,
  getResourceCategories, getResources, getUnits,
} from "../../lib/bcos-api";
import {
  createCategoryAction, createPricingRuleAction, createProfessionalAction,
  createResourceAction, createUnitAction, updateReceptionHoursAction, updateTenantProfileAction,
} from "./actions";

export const dynamic = "force-dynamic";

const dayNames = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"];
const modalityLabel: Record<string,string> = { HOURLY:"Por hora", PERIOD:"Por período", WEEKLY:"Semanal", MONTHLY:"Mensal" };

export default async function TenantAdministrationPage() {
  const [units, categories, resources, professionals, pricingRules, profile] = await Promise.all([
    getUnits(), getResourceCategories(), getResources(), getProfessionals(), getPricingRules(), getTenantProfile(),
  ]);
  const receptionHoursByUnit = new Map(await Promise.all(units.map(async unit => [unit.id, await getReceptionHours(unit.id)] as const)));

  return <main className="admin-page admin-commercial">
    <header className="admin-page-head admin-hero">
      <div><span>ADMINISTRAÇÃO</span><h1>Seu coworking, organizado.</h1><p>Configure a empresa, os espaços e as regras que sustentam a operação diária.</p></div>
      <Link className="admin-users-action" href="/administracao/usuarios">Usuários e acessos →</Link>
    </header>

    <nav className="admin-section-nav admin-section-tabs" aria-label="Administração">
      <a href="#empresa">Empresa</a><a href="#unidades">Unidades</a><a href="#espacos">Espaços</a><a href="#profissionais">Profissionais</a><a href="#precos">Preços</a>
    </nav>

    <section className="admin-overview" aria-label="Resumo da configuração">
      <div><span>UNIDADES</span><strong>{units.length}</strong><small>locais configurados</small></div>
      <div><span>ESPAÇOS</span><strong>{resources.length}</strong><small>recursos cadastrados</small></div>
      <div><span>PROFISSIONAIS</span><strong>{professionals.length}</strong><small>na operação</small></div>
      <div><span>REGRAS DE PREÇO</span><strong>{pricingRules.length}</strong><small>configurações comerciais</small></div>
    </section>

    <section className="admin-content-grid">
      <article id="empresa" className="admin-config-card admin-card-wide">
        <div className="admin-card-heading"><div><span>01 · EMPRESA</span><h2>Dados do negócio</h2><p>Informações que identificam este coworking no BCOS.</p></div><strong>{profile.trade_name}</strong></div>
        <form className="admin-form-grid" action={updateTenantProfileAction}>
          <label>Nome fantasia<input name="trade_name" defaultValue={profile.trade_name} required/></label>
          <label>Razão social<input name="legal_name" defaultValue={profile.legal_name} required/></label>
          <label>CNPJ / CPF<input name="tax_id" defaultValue={profile.tax_id ?? ""}/></label>
          <label>E-mail<input name="email" type="email" defaultValue={profile.email} required/></label>
          <label>Telefone<input name="phone" defaultValue={profile.phone ?? ""}/></label>
          <div className="admin-form-action"><button type="submit">Salvar dados da empresa</button></div>
        </form>
      </article>

      <article id="unidades" className="admin-config-card">
        <div className="admin-card-heading"><div><span>02 · UNIDADES</span><h2>Locais de atendimento</h2><p>Cadastre cada endereço operacional como uma unidade.</p></div><strong>{units.length}</strong></div>
        <div className="admin-chip-list">{units.map(unit=><span key={unit.id}>{unit.name}</span>)}{!units.length&&<small>Nenhuma unidade cadastrada.</small>}</div>
        <form className="admin-inline-form" action={createUnitAction}><input name="name" required placeholder="Nome da unidade"/><input name="timezone" defaultValue="America/Sao_Paulo" required aria-label="Fuso horário"/><button type="submit">Adicionar</button></form>
      </article>

      <article id="espacos" className="admin-config-card">
        <div className="admin-card-heading"><div><span>03 · ESPAÇOS</span><h2>Categorias e recursos</h2><p>Organize salas, cadeiras e demais espaços disponíveis.</p></div><strong>{resources.length}</strong></div>
        <div className="admin-subsection"><h3>Categorias</h3><div className="admin-chip-list">{categories.map(item=><span key={item.id}>{item.name}</span>)}{!categories.length&&<small>Nenhuma categoria.</small>}</div><form className="admin-inline-form" action={createCategoryAction}><input name="name" required placeholder="Ex.: Sala de estética"/><button type="submit">Adicionar categoria</button></form></div>
        <div className="admin-subsection"><h3>Espaços cadastrados</h3><div className="admin-chip-list">{resources.map(item=><span key={item.id}>{item.name}</span>)}{!resources.length&&<small>Nenhum espaço.</small>}</div><form className="admin-form-grid admin-form-compact" action={createResourceAction}><label>Nome<input name="name" required placeholder="Ex.: Sala 01"/></label><label>Unidade<select name="unit_id" required defaultValue=""><option value="" disabled>Selecione</option>{units.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select></label><label>Categoria<select name="category_id" required defaultValue=""><option value="" disabled>Selecione</option>{categories.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select></label><div className="admin-form-action"><button type="submit">Adicionar espaço</button></div></form></div>
      </article>

      <article id="profissionais" className="admin-config-card">
        <div className="admin-card-heading"><div><span>04 · PROFISSIONAIS</span><h2>Equipe profissional</h2><p>Cadastre quem utiliza os espaços do coworking.</p></div><strong>{professionals.length}</strong></div>
        <div className="admin-chip-list">{professionals.map(item=><span key={item.id}>{item.name}</span>)}{!professionals.length&&<small>Nenhum profissional cadastrado.</small>}</div>
        <form className="admin-form-grid admin-form-compact" action={createProfessionalAction}><label>Nome<input name="name" required/></label><label>E-mail<input name="email" type="email"/></label><label>Telefone<input name="phone"/></label><div className="admin-form-action"><button type="submit">Adicionar profissional</button></div></form>
      </article>

      <article className="admin-config-card">
        <div className="admin-card-heading"><div><span>05 · FUNCIONAMENTO</span><h2>Horários por unidade</h2><p>Abra somente a unidade que deseja ajustar.</p></div></div>
        <div className="admin-hours-list">{units.map(unit=>{const hoursByDay=new Map((receptionHoursByUnit.get(unit.id)??[]).map(item=>[item.day_of_week,item]));return <details key={unit.id} className="admin-hours-unit"><summary><span>{unit.name}</span><strong>Editar horários</strong></summary><form className="reception-hours-form" action={updateReceptionHoursAction}><input type="hidden" name="unit_id" value={unit.id}/>{dayNames.map((name,day)=>{const item=hoursByDay.get(day);return <div key={day}><strong>{name}</strong><input name={`opens_${day}`} type="time" defaultValue={item?.opens_at?.slice(0,5)??"08:00"}/><input name={`closes_${day}`} type="time" defaultValue={item?.closes_at?.slice(0,5)??"18:00"}/><label><input name={`closed_${day}`} type="checkbox" defaultChecked={item?.is_closed??false}/> Fechado</label></div>})}<button type="submit">Salvar horários de {unit.name}</button></form></details>})}{!units.length&&<div className="admin-empty">Cadastre uma unidade para configurar os horários.</div>}</div>
      </article>

      <article id="precos" className="admin-config-card admin-card-wide admin-pricing-card">
        <div className="admin-card-heading"><div><span>06 · PREÇOS</span><h2>Regras comerciais</h2><p>Defina como cada espaço será precificado nas reservas.</p></div><strong>{pricingRules.length}</strong></div>
        <div className="admin-pricing-layout">
          <div className="admin-rule-list">{pricingRules.map(rule=><div key={rule.id}><div><strong>{rule.name}</strong><span>{modalityLabel[String(rule.rule_definition?.modality)]??"Regra comercial"}</span></div><small>Prioridade {rule.priority}</small></div>)}{!pricingRules.length&&<div className="admin-empty">Nenhuma regra de preço cadastrada.</div>}</div>
          <form className="admin-form-grid" action={createPricingRuleAction}>
            <label>Nome da tabela<input name="name" required placeholder="Ex.: Sala por hora"/></label>
            <label>Unidade<select name="unit_id" defaultValue=""><option value="">Todas as unidades</option>{units.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
            <label>Categoria<select name="category_id" defaultValue=""><option value="">Todas as categorias</option>{categories.map(x=><option key={x.id} value={x.id}>{x.name}</option>)}</select></label>
            <label>Modalidade<select name="modality" defaultValue="HOURLY" required><option value="HOURLY">Por hora</option><option value="PERIOD">Por período</option><option value="WEEKLY">Semanal</option><option value="MONTHLY">Mensal</option></select></label>
            <label>Preço-base (R$)<input name="base_price_amount" inputMode="decimal" required placeholder="100.00"/></label>
            <label>Hora excedente (R$)<input name="overtime_hourly_price_amount" inputMode="decimal" required placeholder="100.00"/></label>
            <label>Proporcional até (min)<input name="proportional_until_minutes" type="number" min="0" defaultValue="29" required/></label>
            <label>Hora cheia a partir de (min)<input name="full_hour_from_minutes" type="number" min="1" defaultValue="30" required/></label>
            <label className="admin-check"><input name="forgiveness_allowed" type="checkbox"/> Permitir tolerância autorizada</label>
            <details className="admin-advanced"><summary>Opções avançadas</summary><label>Prioridade<input name="priority" type="number" min="0" defaultValue="100" required/></label><label>Penalidade<select name="conflict_penalty_mode" defaultValue=""><option value="">Sem penalidade</option><option value="FIXED_AMOUNT">Valor fixo</option><option value="PERCENTAGE">Percentual</option></select></label><label>Valor<input name="conflict_penalty_value" inputMode="decimal"/></label><label>Válida a partir de<input name="valid_from" type="datetime-local"/></label><label>Válida até<input name="valid_until" type="datetime-local"/></label></details>
            <div className="admin-form-action"><button type="submit">Criar regra de preço</button></div>
          </form>
        </div>
      </article>
    </section>
  </main>;
}
