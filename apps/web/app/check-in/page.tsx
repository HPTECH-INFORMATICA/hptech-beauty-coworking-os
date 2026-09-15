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

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
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

  return (
    <main className="finance-shell">
      <header className="finance-header">
        <div>
          <span className="section-eyebrow">RECEPÇÃO</span>
          <h1>Check-in de reservas</h1>
          <p>Inicie o uso real do espaço a partir de uma reserva confirmada.</p>
        </div>
        <Link className="text-action" href="/">
          Voltar para a central
        </Link>
      </header>

      {error ? (
        <section className="operational-empty">
          <strong>{error}</strong>
        </section>
      ) : eligibleBookings.length === 0 ? (
        <section className="quiet-state">
          <div>
            <strong>Nenhuma reserva confirmada disponível</strong>
            <span>Quando houver uma reserva elegível, o check-in aparecerá aqui.</span>
          </div>
        </section>
      ) : (
        <section className="finance-list">
          {eligibleBookings.map((booking) => {
            const selected = booking.id === requestedBookingId;
            return (
              <article className="finance-card" key={booking.id} data-selected={selected || undefined}>
                <div className="finance-card-heading">
                  <div>
                    <span className="section-eyebrow">
                      {selected ? "RESERVA SELECIONADA" : "RESERVA CONFIRMADA"}
                    </span>
                    <strong>
                      {professionalById.get(booking.professional_id)?.name ??
                        "Profissional"}
                    </strong>
                  </div>
                  <span className="status-pill status-positive">Confirmada</span>
                </div>

                <div className="finance-meta">
                  <span>
                    Espaço: {resourceById.get(booking.resource_id)?.name ?? "Espaço"}
                  </span>
                  <span>
                    {formatDateTime(booking.starts_at)} — {formatDateTime(booking.ends_at)}
                  </span>
                </div>

                <form action={checkInAction}>
                  <input name="booking_id" type="hidden" value={booking.id} />
                  <button className="primary-action" type="submit">
                    Fazer check-in
                  </button>
                </form>
              </article>
            );
          })}
        </section>
      )}
    </main>
  );
}
