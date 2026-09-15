import Link from "next/link";

import {
  getBookings,
  getProfessionals,
  getResources,
  getUnits,
  type Booking,
  type Professional,
  type Resource,
} from "../lib/bcos-api";

export const dynamic = "force-dynamic";

type DashboardData = {
  unitName: string;
  timezone: string;
  resources: Resource[];
  professionals: Professional[];
  bookings: Booking[];
  error: string | null;
};

function dateKey(date: Date, timeZone: string): string {
  const parts = new Intl.DateTimeFormat("en", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);
  const year = parts.find((part) => part.type === "year")?.value ?? "";
  const month = parts.find((part) => part.type === "month")?.value ?? "";
  const day = parts.find((part) => part.type === "day")?.value ?? "";
  return `${year}-${month}-${day}`;
}

function formatTime(value: string, timeZone: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone,
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatDay(timeZone: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone,
    weekday: "long",
    day: "2-digit",
    month: "long",
  }).format(new Date());
}

function normalizeStatus(value: string): string {
  const dictionary: Record<string, string> = {
    ACTIVE: "Ativo", AVAILABLE: "Livre", FREE: "Livre", LIVRE: "Livre",
    RESERVED: "Reservado", CONFIRMED: "Confirmado", PENDING: "Pendente",
    CHECKED_IN: "Em atendimento", COMPLETED: "Concluído", CANCELLED: "Cancelado",
    CLEANING: "Limpeza", MAINTENANCE: "Manutenção", BLOCKED: "Bloqueado",
    OCUPADO: "Em uso", OCCUPIED: "Em uso",
  };
  const status = value.toUpperCase();
  return dictionary[status] ?? value.replaceAll("_", " ");
}

function statusTone(value: string): string {
  const status = value.toUpperCase();
  if (["AVAILABLE", "FREE", "LIVRE", "ACTIVE", "COMPLETED", "CONFIRMED"].includes(status)) return "positive";
  if (["PENDING", "RESERVED", "CLEANING"].includes(status)) return "attention";
  if (["CHECKED_IN", "OCCUPIED", "OCUPADO"].includes(status)) return "live";
  if (["CANCELLED", "BLOCKED", "MAINTENANCE"].includes(status)) return "critical";
  return "neutral";
}

async function loadDashboardData(): Promise<DashboardData> {
  try {
    const units = await getUnits();
    const unit = units.find((item) => item.active) ?? units[0] ?? null;
    const [resources, professionals, bookings] = await Promise.all([
      getResources(unit?.id), getProfessionals(), getBookings(),
    ]);
    return { unitName: unit?.name ?? "Unidade", timezone: unit?.timezone ?? "America/Sao_Paulo", resources, professionals, bookings, error: null };
  } catch (error) {
    console.error("BCOS operational center load failed:", error);
    return { unitName: "Unidade", timezone: "America/Sao_Paulo", resources: [], professionals: [], bookings: [], error: "Não foi possível carregar a operação neste momento." };
  }
}

function cleanUnitName(name: string): string {
  return name.replace(/\s*-\s*homologa[cç][aã]o/gi, "").replace(/\s+homologa[cç][aã]o/gi, "").trim();
}

function Icon({ type }: { type: "resource" | "person" | "search" | "calendar" | "clock" | "arrow" }) {
  if (type === "resource") return <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M4 20V8.8c0-.7.4-1.4 1-1.7l6-3.3c.6-.3 1.3-.3 1.9 0L19 7.1c.6.4 1 1 1 1.7V20M2 20h20M8 20v-5h8v5M8 10h.01M12 10h.01M16 10h.01" /></svg>;
  if (type === "person") return <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM4.5 20c.8-3.5 3.3-5.5 7.5-5.5s6.7 2 7.5 5.5" /></svg>;
  if (type === "search") return <svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="11" cy="11" r="6.5" /><path d="m16 16 4 4" /></svg>;
  if (type === "calendar") return <svg aria-hidden="true" viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="16" rx="3" /><path d="M8 3v4M16 3v4M3 10h18" /></svg>;
  if (type === "clock") return <svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>;
  return <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M5 12h14M14 7l5 5-5 5" /></svg>;
}

function resolveCurrentBooking(bookings: Booking[], now: Date): Booking | undefined {
  const nowMs = now.getTime();
  return bookings.find((booking) => {
    const status = booking.status.toUpperCase();
    return !["CANCELLED", "COMPLETED"].includes(status) && new Date(booking.starts_at).getTime() <= nowMs && nowMs <= new Date(booking.ends_at).getTime();
  });
}

export default async function HomePage() {
  const data = await loadDashboardData();
  const unitName = cleanUnitName(data.unitName);
  const now = new Date();
  const today = dateKey(now, data.timezone);
  const todayBookings = data.bookings.filter((booking) => dateKey(new Date(booking.starts_at), data.timezone) === today && booking.status.toUpperCase() !== "CANCELLED").sort((a, b) => new Date(a.starts_at).getTime() - new Date(b.starts_at).getTime());
  const currentBooking = resolveCurrentBooking(todayBookings, now);
  const upcomingBookings = todayBookings.filter((booking) => new Date(booking.starts_at).getTime() > now.getTime() && booking.status.toUpperCase() !== "COMPLETED").slice(0, 5);
  const completedToday = todayBookings.filter((booking) => booking.status.toUpperCase() === "COMPLETED").length;
  const resourceById = new Map(data.resources.map((resource) => [resource.id, resource]));
  const professionalById = new Map(data.professionals.map((professional) => [professional.id, professional]));
  const activeResources = data.resources.filter((resource) => resource.active);

  return <main className="product-shell">
    <aside className="product-rail">
      <div>
        <div className="rail-brand"><div className="rail-brand-mark">H</div><div className="rail-brand-copy"><strong>HPTECH</strong><span>Beauty Coworking OS</span></div></div>
        <nav className="rail-nav" aria-label="Navegação principal">
          <Link className="rail-link rail-link-active" href="/"><span className="rail-icon"><Icon type="clock" /></span><span>Agora</span></Link>
          <Link className="rail-link" href="/agenda"><span className="rail-icon"><Icon type="calendar" /></span><span>Agenda</span></Link>
          <Link className="rail-link" href="/#espacos"><span className="rail-icon"><Icon type="resource" /></span><span>Espaços</span></Link>
          <Link className="rail-link" href="/#profissionais"><span className="rail-icon"><Icon type="person" /></span><span>Profissionais</span></Link>
          <Link className="rail-link" href="/check-in"><span className="rail-icon"><Icon type="clock" /></span><span>Check-in</span></Link>
          <Link className="rail-link" href="/financeiro"><span className="rail-icon"><Icon type="arrow" /></span><span>Financeiro</span></Link>
        </nav>
      </div>
      <div className="rail-bottom"><div className="tenant-signature"><span className="tenant-logo-placeholder">LB</span><div><strong>{unitName}</strong><span>Ambiente operacional</span></div></div><div className="powered-by"><span>Produto</span><strong>HPTECH PLATFORM</strong></div></div>
    </aside>
    <section className="product-workspace">
      <header className="command-header"><div className="command-heading"><span>Central da Recepção</span><strong>{unitName}</strong></div><button className="global-command" type="button"><span className="global-command-icon"><Icon type="search" /></span><span className="global-command-label">Buscar pessoa, reserva ou espaço</span><kbd>Ctrl K</kbd></button><div className="operator"><div className="operator-copy"><strong>Recepção</strong><span>Operação do dia</span></div><div className="operator-avatar"><Icon type="person" /></div></div></header>
      <div className="operational-canvas">
        <section className="day-heading" id="agora"><div><span className="day-kicker">{formatDay(data.timezone)}</span><h1>O que está acontecendo agora.</h1></div><div className={data.error ? "live-health live-health-error" : "live-health"}><span className="live-health-dot" /><div><strong>{data.error ? "Operação indisponível" : "Operação conectada"}</strong><span>{data.error ?? `${todayBookings.length} reservas hoje`}</span></div></div></section>
        <section className="now-layout"><article className="now-card"><div className="section-heading"><div><span className="section-eyebrow">AGORA</span><h2>Operação em curso</h2></div><span className="section-live-badge">AO VIVO</span></div>
          {data.error ? <div className="operational-empty"><div className="empty-symbol">!</div><div><strong>Não foi possível carregar a operação</strong><p>{data.error}</p></div></div> : currentBooking ? <div className="current-operation"><div className="current-time"><span>INÍCIO</span><strong>{formatTime(currentBooking.starts_at, data.timezone)}</strong></div><div className="current-people"><div className="profile-photo profile-photo-placeholder"><Icon type="person" /></div><div className="current-copy"><span className="current-label">Profissional</span><strong>{professionalById.get(currentBooking.professional_id)?.name ?? "Profissional"}</strong><div className="current-meta"><span>{resourceById.get(currentBooking.resource_id)?.name ?? "Espaço"}</span><span className="meta-separator" /><span>{formatTime(currentBooking.starts_at, data.timezone)} – {formatTime(currentBooking.ends_at, data.timezone)}</span></div></div></div><div className="current-action"><span className={`status-pill status-${statusTone(currentBooking.status)}`}>{normalizeStatus(currentBooking.status)}</span><Link className="primary-action" href="/check-in"><span>Abrir operação</span><Icon type="arrow" /></Link></div></div> : <div className="operational-empty operational-empty-calm"><div className="empty-symbol"><Icon type="clock" /></div><div><strong>Nenhum atendimento em curso agora</strong><p>O próximo movimento da operação aparecerá aqui automaticamente.</p></div></div>}
        </article><aside className="pulse-card"><span className="section-eyebrow">HOJE</span><div className="pulse-number"><strong>{todayBookings.length}</strong><span>reservas</span></div><div className="pulse-row"><span>Concluídas</span><strong>{completedToday}</strong></div><div className="pulse-row"><span>Próximas</span><strong>{upcomingBookings.length}</strong></div><div className="pulse-row"><span>Espaços ativos</span><strong>{activeResources.length}</strong></div></aside></section>
        <section className="agenda-section"><div className="section-heading"><div><span className="section-eyebrow">PRÓXIMOS</span><h2>O ritmo das próximas horas</h2></div><Link className="text-action" href="/agenda"><span>Ver agenda completa</span><Icon type="arrow" /></Link></div>{upcomingBookings.length === 0 ? <div className="quiet-state"><div className="quiet-icon"><Icon type="calendar" /></div><div><strong>Nenhuma próxima reserva</strong><span>A agenda futura do dia está livre.</span></div></div> : <div className="agenda-list">{upcomingBookings.map((booking) => <article className="agenda-row" key={booking.id}><div className="agenda-time"><strong>{formatTime(booking.starts_at, data.timezone)}</strong><span>{formatTime(booking.ends_at, data.timezone)}</span></div><div className="agenda-profile"><div className="profile-photo agenda-avatar"><Icon type="person" /></div><div><strong>{professionalById.get(booking.professional_id)?.name ?? "Profissional"}</strong><span>{resourceById.get(booking.resource_id)?.name ?? "Espaço"}</span></div></div><span className={`status-pill status-${statusTone(booking.status)}`}>{normalizeStatus(booking.status)}</span></article>)}</div>}</section>
        <section className="spaces-section" id="espacos"><div className="section-heading"><div><span className="section-eyebrow">ESPAÇOS</span><h2>O coworking agora</h2></div><span className="section-count">{activeResources.length} {activeResources.length === 1 ? "espaço ativo" : "espaços ativos"}</span></div><div className="resource-grid">{activeResources.map((resource) => <article className="resource-card" key={resource.id}><div className="resource-visual"><div className="resource-visual-icon"><Icon type="resource" /></div><span className={`status-pill status-${statusTone(resource.operational_status)}`}>{normalizeStatus(resource.operational_status)}</span></div><div className="resource-body"><span className="resource-kicker">ESPAÇO</span><strong>{resource.name}</strong><div className="resource-next"><span>STATUS OPERACIONAL</span><strong>{normalizeStatus(resource.operational_status)}</strong></div></div></article>)}</div></section>
        <section className="people-section" id="profissionais"><div className="section-heading"><div><span className="section-eyebrow">PROFISSIONAIS</span><h2>Pessoas que movimentam a operação</h2></div><span className="section-count">{data.professionals.length} cadastrados</span></div><div className="people-grid">{data.professionals.map((professional) => <article className="person-card" key={professional.id}><div className="profile-photo person-avatar"><Icon type="person" /></div><div className="person-copy"><strong>{professional.name}</strong><span>{professional.email ?? "Profissional do coworking"}</span><div className="person-next"><span>STATUS</span><strong>{normalizeStatus(professional.status)}</strong></div></div></article>)}</div></section>
      </div>
    </section>
  </main>;
}
