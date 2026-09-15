import Link from "next/link";

import {
  getMyBookings,
  getMyInvoices,
  type Booking,
  type Invoice,
} from "../../lib/bcos-api";

export const dynamic = "force-dynamic";

function money(value: string, currency: string): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency,
  }).format(Number(value));
}

function dateTime(value: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

export default async function ProfessionalPage() {
  let bookings: Booking[] = [];
  let invoices: Invoice[] = [];
  let error: string | null = null;

  try {
    [bookings, invoices] = await Promise.all([getMyBookings(), getMyInvoices()]);
  } catch (caught) {
    console.error("BCOS professional portal load failed:", caught);
    error = "Não foi possível carregar seu portal neste momento.";
  }

  const openInvoices = invoices.filter(
    (invoice) => invoice.status === "OPEN" || invoice.status === "PARTIALLY_PAID",
  );

  return (
    <main className="finance-shell">
      <header className="finance-header">
        <div>
          <span className="section-eyebrow">PORTAL DO PROFISSIONAL</span>
          <h1>Minha operação</h1>
          <p>Consulte suas reservas e suas faturas sem acessar dados de outros profissionais.</p>
        </div>
        <Link className="primary-action" href="/">
          Voltar para a central
        </Link>
      </header>

      <section className="finance-summary" aria-label="Resumo do profissional">
        <article className="pulse-card">
          <span className="section-eyebrow">RESERVAS</span>
          <div className="pulse-number"><strong>{bookings.length}</strong></div>
        </article>
        <article className="pulse-card">
          <span className="section-eyebrow">FATURAS EM ABERTO</span>
          <div className="pulse-number"><strong>{openInvoices.length}</strong></div>
        </article>
        <article className="pulse-card">
          <span className="section-eyebrow">A PAGAR</span>
          <div className="pulse-number">
            <strong>{money(String(openInvoices.reduce((total, invoice) => total + Number(invoice.total_amount), 0)), "BRL")}</strong>
          </div>
        </article>
      </section>

      {error ? <section className="operational-empty"><strong>{error}</strong></section> : null}

      {!error ? (
        <>
          <section className="finance-list" aria-label="Minhas reservas">
            <div className="finance-header"><div><span className="section-eyebrow">AGENDA</span><h2>Minhas reservas</h2></div></div>
            {bookings.length === 0 ? (
              <div className="quiet-state"><div><strong>Nenhuma reserva encontrada</strong><span>Suas reservas aparecerão aqui.</span></div></div>
            ) : bookings.map((booking) => (
              <article className="finance-card" key={booking.id}>
                <div className="finance-card-heading">
                  <div><span className="section-eyebrow">RESERVA</span><strong>{booking.id.slice(0, 8).toUpperCase()}</strong></div>
                  <span className="status-pill status-attention">{booking.status.replaceAll("_", " ")}</span>
                </div>
                <div className="finance-meta"><span>Início: {dateTime(booking.starts_at)}</span><span>Fim: {dateTime(booking.ends_at)}</span></div>
              </article>
            ))}
          </section>

          <section className="finance-list" aria-label="Minhas faturas">
            <div className="finance-header"><div><span className="section-eyebrow">FINANCEIRO</span><h2>Minhas faturas</h2></div></div>
            {invoices.length === 0 ? (
              <div className="quiet-state"><div><strong>Nenhuma fatura encontrada</strong><span>Suas cobranças aparecerão aqui.</span></div></div>
            ) : invoices.map((invoice) => (
              <article className="finance-card" key={invoice.id}>
                <div className="finance-card-heading">
                  <div><span className="section-eyebrow">FATURA</span><strong>{invoice.id.slice(0, 8).toUpperCase()}</strong></div>
                  <span className={`status-pill status-${invoice.status === "PAID" ? "positive" : "attention"}`}>{invoice.status.replaceAll("_", " ")}</span>
                </div>
                <div className="finance-amount"><span>Total</span><strong>{money(invoice.total_amount, invoice.currency)}</strong></div>
              </article>
            ))}
          </section>
        </>
      ) : null}
    </main>
  );
}
