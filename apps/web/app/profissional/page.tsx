import Link from "next/link";

import { getMyBookings, getMyCommercialAvailability, getMyInvoices, getResourceCategories, getUnits, type Booking, type Invoice, type ProfessionalCommercialAvailability, type ResourceCategory, type Unit } from "../../lib/bcos-api";
import { createMyBookingAction } from "./actions";

export const dynamic = "force-dynamic";

function money(value: string, currency: string): string { return new Intl.NumberFormat("pt-BR", { style: "currency", currency }).format(Number(value)); }
function dateTime(value: string): string { return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)); }
function bookingStatus(status: string): string { const labels: Record<string, string> = { PENDING: "Pendente", CONFIRMED: "Confirmada", CANCELLED: "Cancelada", COMPLETED: "Concluída" }; return labels[status] ?? status.replaceAll("_", " "); }
function invoiceStatus(status: string): string { const labels: Record<string, string> = { OPEN: "Em aberto", PARTIALLY_PAID: "Parcialmente paga", PAID: "Paga", CANCELLED: "Cancelada" }; return labels[status] ?? status.replaceAll("_", " "); }
function pricingModality(value: string | null): string { const labels: Record<string, string> = { HOURLY: "por hora", PERIOD: "por período", WEEKLY: "semanal", MONTHLY: "mensal" }; return value ? (labels[value] ?? value) : ""; }
function localDateTimeInZoneToIso(value: string, timeZone: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value);
  if (!match) throw new Error("Data e hora inválidas.");
  const [, year, month, day, hour, minute] = match;
  const wanted = Date.UTC(Number(year), Number(month) - 1, Number(day), Number(hour), Number(minute));
  let instant = wanted;
  const formatter = new Intl.DateTimeFormat("en-CA", { timeZone, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const parts = Object.fromEntries(formatter.formatToParts(new Date(instant)).map((part) => [part.type, part.value]));
    const represented = Date.UTC(Number(parts.year), Number(parts.month) - 1, Number(parts.day), Number(parts.hour), Number(parts.minute));
    instant += wanted - represented;
  }
  const finalParts = Object.fromEntries(formatter.formatToParts(new Date(instant)).map((part) => [part.type, part.value]));
  if (`${finalParts.year}-${finalParts.month}-${finalParts.day}T${finalParts.hour}:${finalParts.minute}` !== value) throw new Error("Horário local inválido para o fuso da unidade.");
  return new Date(instant).toISOString();
}


export default async function ProfessionalPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const params = await searchParams;
  const unitId = typeof params.unit_id === "string" ? params.unit_id : "";
  const categoryId = typeof params.category_id === "string" ? params.category_id : "";
  const startsAt = typeof params.starts_at === "string" ? params.starts_at : "";
  const endsAt = typeof params.ends_at === "string" ? params.ends_at : "";
  let units: Unit[] = [];
  let categories: ResourceCategory[] = [];
  let commercial: ProfessionalCommercialAvailability | null = null;
  let bookings: Booking[] = [];
  let invoices: Invoice[] = [];
  let error: string | null = null;
  try { [bookings, invoices, units, categories] = await Promise.all([getMyBookings(), getMyInvoices(), getUnits(), getResourceCategories()]); if (unitId && startsAt && endsAt) { const selectedUnit = units.find((unit) => unit.id === unitId && unit.active); if (!selectedUnit) throw new Error("Unidade selecionada não está disponível."); const startsAtIso = localDateTimeInZoneToIso(startsAt, selectedUnit.timezone); const endsAtIso = localDateTimeInZoneToIso(endsAt, selectedUnit.timezone); if (new Date(endsAtIso).getTime() <= new Date(startsAtIso).getTime()) throw new Error("O fim deve ser posterior ao início."); commercial = await getMyCommercialAvailability({ unitId, startsAt: startsAtIso, endsAt: endsAtIso, categoryId: categoryId || undefined }); } } catch (caught) { console.error("BCOS professional portal load failed:", caught); error = "Não foi possível carregar seu portal neste momento."; }
  const openInvoices = invoices.filter((invoice) => invoice.status === "OPEN" || invoice.status === "PARTIALLY_PAID");
  const upcomingBookings = bookings.filter((booking) => booking.status === "PENDING" || booking.status === "CONFIRMED");
  return (
    <main className="finance-shell">
      <header className="finance-header"><div><span className="section-eyebrow">PORTAL DO PROFISSIONAL</span><h1>Minha operação</h1><p>Suas reservas e cobranças, restritas ao seu próprio acesso.</p></div><Link className="primary-action" href="/">Voltar para a central</Link></header>
      <section className="finance-summary" aria-label="Resumo do profissional">
        <article className="pulse-card"><span className="section-eyebrow">PRÓXIMAS RESERVAS</span><div className="pulse-number"><strong>{upcomingBookings.length}</strong></div></article>
        <article className="pulse-card"><span className="section-eyebrow">FATURAS EM ABERTO</span><div className="pulse-number"><strong>{openInvoices.length}</strong></div></article>
        <article className="pulse-card"><span className="section-eyebrow">A PAGAR</span><div className="pulse-number"><strong>{money(String(openInvoices.reduce((total, invoice) => total + Number(invoice.total_amount), 0)), "BRL")}</strong></div></article>
      </section>
      <section className="finance-list" aria-label="Nova reserva"><div className="finance-header"><div><span className="section-eyebrow">NOVA RESERVA</span><h2>Encontrar espaço e horário</h2><p>Escolha a unidade e o período. Disponibilidade e condição comercial são confirmadas pelo servidor.</p></div></div><form method="get" className="tenant-invite-form"><select name="unit_id" required defaultValue={unitId}><option value="">Selecione a unidade</option>{units.filter(unit => unit.active).map(unit => <option key={unit.id} value={unit.id}>{unit.name}</option>)}</select><select name="category_id" defaultValue={categoryId}><option value="">Todas as categorias</option>{categories.filter(category => category.active).map(category => <option key={category.id} value={category.id}>{category.name}</option>)}</select><input name="starts_at" type="datetime-local" required defaultValue={startsAt}/><input name="ends_at" type="datetime-local" required defaultValue={endsAt}/><button type="submit">Consultar disponibilidade</button></form>{commercial ? <div className="finance-list">{commercial.resources.length === 0 ? <div className="quiet-state"><div><strong>Nenhum espaço encontrado</strong><span>Tente outro período ou categoria.</span></div></div> : commercial.resources.map(option => <article className="finance-card" key={option.resource_id}><div className="finance-card-heading"><div><span className="section-eyebrow">ESPAÇO</span><strong>{option.resource_name}</strong></div><span className={`status-pill status-${option.available ? "positive" : "attention"}`}>{option.available ? "Disponível" : "Indisponível"}</span></div>{option.unavailable_reason ? <p>{option.unavailable_reason}</p> : null}{option.available && option.price_amount && option.price_currency ? <div className="finance-amount"><span>Valor {option.price_modality ? `(${pricingModality(option.price_modality)})` : ""}</span><strong>{money(option.price_amount, option.price_currency)}</strong></div> : null}{option.available ? <form action={createMyBookingAction}><input type="hidden" name="unit_id" value={commercial.unit_id}/><input type="hidden" name="resource_id" value={option.resource_id}/><input type="hidden" name="starts_at" value={commercial.starts_at}/><input type="hidden" name="ends_at" value={commercial.ends_at}/><label>Observação opcional<input name="notes" placeholder="Informação sobre a reserva"/></label><button type="submit">Revisar e confirmar reserva</button></form> : null}</article>)}</div> : null}</section>
      {error ? <section className="operational-empty"><strong>{error}</strong></section> : null}
      {!error ? <>
        <section className="finance-list" aria-label="Minhas reservas"><div className="finance-header"><div><span className="section-eyebrow">AGENDA</span><h2>Minhas reservas</h2></div></div>{bookings.length === 0 ? <div className="quiet-state"><div><strong>Nenhuma reserva encontrada</strong><span>Suas reservas aparecerão aqui.</span></div></div> : bookings.map((booking) => <article className="finance-card" key={booking.id}><div className="finance-card-heading"><div><span className="section-eyebrow">RESERVA</span><strong>{dateTime(booking.starts_at)}</strong></div><span className={`status-pill status-${booking.status === "CONFIRMED" || booking.status === "COMPLETED" ? "positive" : "attention"}`}>{bookingStatus(booking.status)}</span></div><div className="finance-meta"><span>Início: {dateTime(booking.starts_at)}</span><span>Fim: {dateTime(booking.ends_at)}</span></div></article>)}</section>
        <section className="finance-list" aria-label="Minhas faturas"><div className="finance-header"><div><span className="section-eyebrow">FINANCEIRO</span><h2>Minhas faturas</h2></div></div>{invoices.length === 0 ? <div className="quiet-state"><div><strong>Nenhuma fatura encontrada</strong><span>Suas cobranças aparecerão aqui.</span></div></div> : invoices.map((invoice) => <article className="finance-card" key={invoice.id}><div className="finance-card-heading"><div><span className="section-eyebrow">COBRANÇA</span><strong>{new Intl.DateTimeFormat("pt-BR").format(new Date(invoice.created_at))}</strong></div><span className={`status-pill status-${invoice.status === "PAID" ? "positive" : "attention"}`}>{invoiceStatus(invoice.status)}</span></div><div className="finance-amount"><span>Total</span><strong>{money(invoice.total_amount, invoice.currency)}</strong></div></article>)}</section>
      </> : null}
    </main>
  );
}
