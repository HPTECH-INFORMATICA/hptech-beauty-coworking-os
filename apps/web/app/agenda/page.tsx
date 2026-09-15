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
  let timezone = "America/Sao_Paulo";
  let error: string | null = null;

  try {
    const units = await getUnits();
    const unit = units.find((item) => item.active) ?? units[0];
    timezone = unit?.timezone ?? timezone;
    [bookings, professionals, resources] = await Promise.all([getBookings(), getProfessionals(), getResources(unit?.id)]);
  } catch (caught) {
    console.error("BCOS agenda load failed:", caught);
    error = "Não foi possível carregar a agenda neste momento.";
  }

  const professionalById = new Map(professionals.map((item) => [item.id, item]));
  const resourceById = new Map(resources.map((item) => [item.id, item]));
  const ordered = [...bookings].sort((a, b) => new Date(a.starts_at).getTime() - new Date(b.starts_at).getTime());

  return <main className="finance-shell">
    <header className="finance-header"><div><span className="section-eyebrow">RECEPÇÃO</span><h1>Agenda operacional</h1><p>Reservas do coworking em ordem cronológica, com profissional, espaço e situação atual.</p></div><Link className="primary-action" href="/">Voltar para a central</Link></header>
    {error ? <section className="operational-empty"><strong>{error}</strong></section> : ordered.length === 0 ? <section className="quiet-state"><div><strong>Nenhuma reserva encontrada</strong><span>As novas reservas aparecerão aqui assim que forem registradas.</span></div></section> : <section className="finance-list">{ordered.map((booking) => <article className="finance-card" key={booking.id}><div className="finance-card-heading"><div><span className="section-eyebrow">{formatDate(booking.starts_at, timezone)}</span><strong>{formatTime(booking.starts_at, timezone)} — {formatTime(booking.ends_at, timezone)}</strong></div><span className={`status-pill status-${booking.status.toUpperCase() === "CONFIRMED" || booking.status.toUpperCase() === "COMPLETED" ? "positive" : booking.status.toUpperCase() === "CHECKED_IN" ? "live" : "attention"}`}>{statusLabel(booking.status)}</span></div><div className="finance-meta"><span>Profissional: {professionalById.get(booking.professional_id)?.name ?? "Profissional"}</span><span>Espaço: {resourceById.get(booking.resource_id)?.name ?? "Espaço"}</span></div>{booking.status.toUpperCase() === "CONFIRMED" ? <Link className="primary-action" href="/check-in">Ir para check-in</Link> : null}</article>)}</section>}
  </main>;
}
