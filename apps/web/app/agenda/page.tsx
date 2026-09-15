import Link from "next/link";

import {
  getBookings,
  getProfessionals,
  getResources,
  getUnits,
  type Booking,
  type Professional,
  type Resource,
} from "../../lib/bcos-api";
import {
  confirmBookingAction,
  createBookingAction,
} from "../operations/actions";

export const dynamic = "force-dynamic";

function formatDate(value: string, timeZone: string): string {
  return new Intl.DateTimeFormat("pt-BR", { timeZone, weekday: "short", day: "2-digit", month: "short" }).format(new Date(value));
}

function formatTime(value: string, timeZone: string): string {
  return new Intl.DateTimeFormat("pt-BR", { timeZone, hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = { CONFIRMED: "Confirmada", PENDING: "Pendente", CHECKED_IN: "Em atendimento", COMPLETED: "Concluída", CANCELLED: "Cancelada" };
  return labels[status.toUpperCase()] ?? status.replaceAll("_", " ");
}

export default async function AgendaPage() {
  let bookings: Booking[] = [];
  let professionals: Professional[] = [];
  let resources: Resource[] = [];
  let unitId = "";
  let timezone = "America/Sao_Paulo";
  let error: string | null = null;

  try {
    const units = await getUnits();
    const unit = units.find((item) => item.active) ?? units[0];
    unitId = unit?.id ?? "";
    timezone = unit?.timezone ?? timezone;
    [bookings, professionals, resources] = await Promise.all([getBookings(), getProfessionals(), getResources(unit?.id)]);
  } catch (caught) {
    console.error("BCOS agenda load failed:", caught);
    error = "Não foi possível carregar a agenda neste momento.";
  }

  const professionalById = new Map(professionals.map((item) => [item.id, item]));
  const resourceById = new Map(resources.map((item) => [item.id, item]));
  const ordered = [...bookings].sort((a, b) => new Date(a.starts_at).getTime() - new Date(b.starts_at).getTime());
  const activeResources = resources.filter((item) => item.active);
  const activeProfessionals = professionals.filter((item) => item.status.toUpperCase() === "ACTIVE");
  const canCreate = unitId !== "" && activeResources.length > 0 && activeProfessionals.length > 0;

  return <main className="finance-shell">
    <header className="finance-header"><div><span className="section-eyebrow">RECEPÇÃO</span><h1>Agenda operacional</h1><p>Crie a reserva, confirme a ocupação planejada e conduza o atendimento até o check-in.</p></div><Link className="primary-action" href="/">Voltar para a central</Link></header>

    {!error ? <section className="finance-card">
      <div className="finance-card-heading"><div><span className="section-eyebrow">NOVA RESERVA</span><strong>Registrar horário</strong></div></div>
      {canCreate ? <form action={createBookingAction} className="finance-list">
        <input type="hidden" name="unit_id" value={unitId} />
        <input type="hidden" name="timezone" value={timezone} />
        <label>Profissional<select className="field" name="professional_id" required defaultValue=""><option value="" disabled>Selecione o profissional</option>{activeProfessionals.map((professional) => <option key={professional.id} value={professional.id}>{professional.name}</option>)}</select></label>
        <label>Espaço<select className="field" name="resource_id" required defaultValue=""><option value="" disabled>Selecione o espaço</option>{activeResources.map((resource) => <option key={resource.id} value={resource.id}>{resource.name}</option>)}</select></label>
        <label>Início<input className="field" type="datetime-local" name="starts_at" required /></label>
        <label>Fim<input className="field" type="datetime-local" name="ends_at" required /></label>
        <label>Observação<input className="field" type="text" name="notes" /></label>
        <button className="primary-action" type="submit">Criar reserva</button>
      </form> : <div className="quiet-state"><div><strong>Cadastro operacional incompleto</strong><span>É necessário ter unidade, espaço e profissional ativos para registrar uma reserva.</span></div></div>}
    </section> : null}

    {error ? <section className="operational-empty"><strong>{error}</strong></section> : ordered.length === 0 ? <section className="quiet-state"><div><strong>Nenhuma reserva encontrada</strong><span>Registre a primeira reserva pelo formulário acima.</span></div></section> : <section className="finance-list">{ordered.map((booking) => <article className="finance-card" key={booking.id}><div className="finance-card-heading"><div><span className="section-eyebrow">{formatDate(booking.starts_at, timezone)}</span><strong>{formatTime(booking.starts_at, timezone)} — {formatTime(booking.ends_at, timezone)}</strong></div><span className={`status-pill status-${booking.status.toUpperCase() === "CONFIRMED" || booking.status.toUpperCase() === "COMPLETED" ? "positive" : booking.status.toUpperCase() === "CHECKED_IN" ? "live" : "attention"}`}>{statusLabel(booking.status)}</span></div><div className="finance-meta"><span>Profissional: {professionalById.get(booking.professional_id)?.name ?? "Profissional"}</span><span>Espaço: {resourceById.get(booking.resource_id)?.name ?? "Espaço"}</span></div>{booking.status.toUpperCase() === "PENDING" ? <form action={confirmBookingAction}><input type="hidden" name="booking_id" value={booking.id} /><button className="primary-action" type="submit">Confirmar reserva</button></form> : null}{booking.status.toUpperCase() === "CONFIRMED" ? <Link className="primary-action" href={`/check-in?booking=${encodeURIComponent(booking.id)}`}>Ir para check-in</Link> : null}</article>)}</section>}
  </main>;
}
