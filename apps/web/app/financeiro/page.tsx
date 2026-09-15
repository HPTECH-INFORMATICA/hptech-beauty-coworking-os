import Link from "next/link";

import { getInvoices, type Invoice } from "../../lib/bcos-api";
import { closeInvoiceAction, confirmPixAction } from "../operations/actions";

export const dynamic = "force-dynamic";

function money(value: string, currency: string): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency,
  }).format(Number(value));
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    OPEN: "Em aberto",
    PARTIALLY_PAID: "Parcialmente paga",
    PAID: "Paga",
    CANCELLED: "Cancelada",
  };
  return labels[status] ?? status.replaceAll("_", " ");
}

export default async function FinancePage() {
  let invoices: Invoice[] = [];
  let error: string | null = null;

  try {
    invoices = await getInvoices({ limit: 50, offset: 0 });
  } catch (caught) {
    console.error("BCOS finance load failed:", caught);
    error = "Não foi possível carregar o financeiro neste momento.";
  }

  const openInvoices = invoices.filter(
    (invoice) => invoice.status === "OPEN" || invoice.status === "PARTIALLY_PAID",
  );
  const receivable = openInvoices.reduce(
    (total, invoice) => total + Number(invoice.total_amount),
    0,
  );

  return (
    <main className="finance-shell">
      <header className="finance-header">
        <div>
          <span className="section-eyebrow">FINANCEIRO</span>
          <h1>Faturas e recebimentos</h1>
          <p>Acompanhe cobranças geradas pela operação e confirme recebimentos PIX.</p>
        </div>
        <Link className="primary-action" href="/">
          Voltar para a operação
        </Link>
      </header>

      <section className="finance-summary" aria-label="Resumo financeiro">
        <article className="pulse-card">
          <span className="section-eyebrow">EM ABERTO</span>
          <div className="pulse-number">
            <strong>{openInvoices.length}</strong>
            <span>faturas</span>
          </div>
        </article>
        <article className="pulse-card">
          <span className="section-eyebrow">A RECEBER</span>
          <div className="pulse-number">
            <strong>{money(String(receivable), "BRL")}</strong>
          </div>
        </article>
        <article className="pulse-card">
          <span className="section-eyebrow">TOTAL</span>
          <div className="pulse-number">
            <strong>{invoices.length}</strong>
            <span>faturas</span>
          </div>
        </article>
      </section>

      {error ? (
        <section className="operational-empty">
          <strong>{error}</strong>
        </section>
      ) : invoices.length === 0 ? (
        <section className="quiet-state">
          <div>
            <strong>Nenhuma fatura encontrada</strong>
            <span>As cobranças geradas pela operação aparecerão aqui.</span>
          </div>
        </section>
      ) : (
        <section className="finance-list">
          {invoices.map((invoice) => {
            const canReceive =
              invoice.status === "OPEN" || invoice.status === "PARTIALLY_PAID";
            const canClose =
              canReceive &&
              invoice.source_usage_id === null &&
              !invoice.manual_closed_at;

            return (
              <article className="finance-card" key={invoice.id}>
                <div className="finance-card-heading">
                  <div>
                    <span className="section-eyebrow">FATURA</span>
                    <strong>{invoice.id.slice(0, 8).toUpperCase()}</strong>
                  </div>
                  <span
                    className={`status-pill status-${invoice.status === "PAID" ? "positive" : "attention"}`}
                  >
                    {statusLabel(invoice.status)}
                  </span>
                </div>

                <div className="finance-amount">
                  <span>Total</span>
                  <strong>{money(invoice.total_amount, invoice.currency)}</strong>
                </div>

                <div className="finance-meta">
                  <span>Profissional: {invoice.professional_id.slice(0, 8)}</span>
                  <span>
                    Criada em{" "}
                    {new Intl.DateTimeFormat("pt-BR").format(
                      new Date(invoice.created_at),
                    )}
                  </span>
                </div>

                {canReceive ? (
                  <form action={confirmPixAction} className="finance-payment-form">
                    <input name="invoice_id" type="hidden" value={invoice.id} />
                    <label>
                      <span>Valor recebido via PIX</span>
                      <input
                        inputMode="decimal"
                        name="amount"
                        placeholder="0,00"
                        required
                        type="number"
                        min="0.01"
                        step="0.01"
                      />
                    </label>
                    <label>
                      <span>Referência</span>
                      <input name="reference" placeholder="Comprovante ou observação" />
                    </label>
                    <button className="primary-action" type="submit">
                      Confirmar PIX
                    </button>
                  </form>
                ) : null}

                {canClose ? (
                  <form action={closeInvoiceAction}>
                    <input name="invoice_id" type="hidden" value={invoice.id} />
                    <button className="text-action" type="submit">
                      Encerrar fatura manual
                    </button>
                  </form>
                ) : null}
              </article>
            );
          })}
        </section>
      )}
    </main>
  );
}
