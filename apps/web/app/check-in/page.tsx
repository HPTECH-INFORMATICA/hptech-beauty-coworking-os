import Link from "next/link";

import {
  getBookings,
  getProfessionals,
  getResources,
  type Booking,
  type Professional,
  type Resource,
} from "../../lib/bcos-api";
import { checkInAction } from "../operations/actions";

export const dynamic = "force-dynamic";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

function first(value: string | string[] | undefined): string {
  return typeof value === "string" ? value : "";
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    weekday: "long",
    day: "2-digit",
    month: "long",
    timeZone: "America/Sao_Paulo",
  }).format(new Date(value));
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "America/Sao_Paulo",
  }).format(new Date(value));
}

export default async function CheckInPage({
  searchParams = Promise.resolve({}),
}: {
  searchParams?: SearchParams;
} = {}) {
  const query = await searchParams;
  const requestedBookingId = first(query.booking);
  let error: string | null = null;
  let bookings: Booking[] = [];
  let professionals: Professional[] = [];
  let resources: Resource[] = [];

  try {
    [bookings, professionals, resources] = await Promise.all([
      getBookings(),
      getProfessionals(),
      getResources(),
    ]);
  } catch (caught) {
    console.error("BCOS check-in workspace load failed:", caught);
    error = "Não foi possível carregar as reservas neste momento.";
  }

  const professionalById = new Map(
    professionals.map((professional) => [professional.id, professional]),
  );
  const resourceById = new Map(resources.map((resource) => [resource.id, resource]));
  const eligibleBookings = bookings
    .filter((booking) => booking.status.toUpperCase() === "CONFIRMED")
    .sort((left, right) => {
      if (left.id === requestedBookingId && right.id !== requestedBookingId) return -1;
      if (right.id === requestedBookingId && left.id !== requestedBookingId) return 1;
      return new Date(left.starts_at).getTime() - new Date(right.starts_at).getTime();
    });

  const selectedBooking = eligibleBookings.find((booking) => booking.id === requestedBookingId);

  return (
    <main className="agenda-shell">
      <header className="agenda-topbar">
        <div className="agenda-brand">
          <span className="agenda-brand-mark">H</span>
          <div>
            <strong>HPTECH Beauty Coworking OS</strong>
            <span>Central da Recepção</span>
          </div>
        </div>
        <nav className="agenda-nav">
          <Link href="/">Agora</Link>
          <Link href="/agenda">Agenda</Link>
          <Link className="active" href="/check-in">Check-in</Link>
          <Link href="/financeiro">Financeiro</Link>
        </nav>
      </header>

      <div className="agenda-canvas checkin-canvas">
        <section className="agenda-hero">
          <div>
            <span className="section-eyebrow">RECEPÇÃO • CHECK-IN</span>
            <h1>Check-in de reservas</h1>
            <p>Confirme a chegada e inicie o uso real do espaço a partir de uma reserva confirmada.</p>
          </div>
          <div className="agenda-hero-actions">
            <Link className="text-action" href="/agenda">Ver agenda</Link>
            <Link className="primary-action" href="/">Voltar para a central</Link>
          </div>
        </section>

        <section className="checkin-kpis">
          <div className="agenda-kpi">
            <span>PRONTAS PARA CHECK-IN</span>
            <strong>{eligibleBookings.length}</strong>
          </div>
          <div className="agenda-kpi">
            <span>RESERVA SELECIONADA</span>
            <strong>{selectedBooking ? "1" : "0"}</strong>
          </div>
          <div className="checkin-guidance">
            <span className="section-eyebrow">FLUXO OPERACIONAL</span>
            <strong>Reserva confirmada → Check-in → Uso</strong>
            <p>O check-in apenas inicia o uso real. As regras de ocupação continuam sob autoridade do domínio.</p>
          </div>
        </section>

        {error ? (
          <section className="operational-empty">
            <strong>{error}</strong>
          </section>
        ) : eligibleBookings.length === 0 ? (
          <section className="checkin-empty">
            <span className="section-eyebrow">SEM AÇÕES PENDENTES</span>
            <strong>Nenhuma reserva confirmada disponível</strong>
            <p>Quando houver uma reserva elegível, ela aparecerá aqui pronta para iniciar o atendimento.</p>
            <Link className="primary-action" href="/agenda">Ir para a agenda</Link>
          </section>
        ) : (
          <section className="checkin-board">
            <header className="checkin-board-head">
              <div>
                <span className="section-eyebrow">CHEGADAS</span>
                <h2>Reservas aguardando check-in</h2>
              </div>
              <span>{eligibleBookings.length} {eligibleBookings.length === 1 ? "reserva" : "reservas"}</span>
            </header>

            <div className="checkin-list">
              {eligibleBookings.map((booking) => {
                const selected = booking.id === requestedBookingId;
                return (
                  <article className="checkin-card" key={booking.id} data-selected={selected || undefined}>
                    <div className="checkin-time">
                      <strong>{formatTime(booking.starts_at)}</strong>
                      <span>até {formatTime(booking.ends_at)}</span>
                    </div>
                    <div className="checkin-person">
                      <span className="section-eyebrow">
                        {selected ? "RESERVA SELECIONADA" : formatDate(booking.starts_at)}
                      </span>
                      <strong>
                        {professionalById.get(booking.professional_id)?.name ?? "Profissional"}
                      </strong>
                      <span>{resourceById.get(booking.resource_id)?.name ?? "Espaço"}</span>
                    </div>
                    <div className="checkin-action">
                      <span className="status-pill status-positive">Confirmada</span>
                      <form action={checkInAction}>
                        <input name="booking_id" type="hidden" value={booking.id} />
                        <button className="primary-action" type="submit">Fazer check-in</button>
                      </form>
                    </div>
                  </article>
                );
              })}
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
