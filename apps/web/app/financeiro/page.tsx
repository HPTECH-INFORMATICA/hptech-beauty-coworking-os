import Link from "next/link";

import { getInvoice, getInvoices, getProfessionals, type Invoice, type InvoiceDetail, type Professional } from "../../lib/bcos-api";
import { closeInvoiceAction, confirmPixAction } from "../operations/actions";

export const dynamic = "force-dynamic";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function money(value: string, currency: string): string {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency }).format(Number(value));
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = { OPEN: "Em aberto", PARTIALLY_PAID: "Parcialmente paga", PAID: "Paga", CANCELLED: "Cancelada" };
  return labels[status] ?? status.replaceAll("_", " ");
}

function invoiceContainsUsage(invoice: Invoice, detail: InvoiceDetail | undefined, usageId: string | undefined): boolean {
  if (!usageId) return false;
  return invoice.source_usage_id === usageId || detail?.items.some((item) => item.usage_id === usageId) === true;
}

export default async function FinancePage({ searchParams }: { searchParams?: SearchParams }) {
  const query = searchParams ? await searchParams : {};
  const requestedUsageId = first(query.usage);
  let invoices: Invoice[] = [];
  let professionals: Professional[] = [];
  let details = new Map<string, InvoiceDetail>();
  let error: string | null = null;

  try {
    [invoices, professionals] = await Promise.all([getInvoices({ limit: 50, offset: 0 }), getProfessionals()]);
    const loadedDetails = await Promise.all(invoices.map((invoice) => getInvoice(invoice.id)));
    details = new Map(loadedDetails.map((detail) => [detail.id, detail]));
  } catch (caught) {
    console.error("BCOS finance load failed:", caught);
    error = "Não foi possível carregar o financeiro neste momento.";
  }

  const professionalById = new Map(professionals.map((professional) => [professional.id, professional]));
  const openInvoices = invoices.filter((invoice) => invoice.status === "OPEN" || invoice.status === "PARTIALLY_PAID");
  const receivable = openInvoices.reduce((total, invoice) => total + Number(details.get(invoice.id)?.remaining_amount ?? invoice.total_amount), 0);
  const selectedInvoice = requestedUsageId
    ? invoices.find((invoice) => invoiceContainsUsage(invoice, details.get(invoice.id), requestedUsageId))
    : undefined;
  const billingPending = requestedUsageId !== undefined && selectedInvoice === undefined && error === null;
  const sortedInvoices = [...invoices].sort((left, right) => {
    const leftSelected = invoiceContainsUsage(left, details.get(left.id), requestedUsageId);
    const rightSelected = invoiceContainsUsage(right, details.get(right.id), requestedUsageId);
    if (leftSelected !== rightSelected) return leftSelected ? -1 : 1;
    return 0;
  });

  return (
    <main className="finance-shell">
      <header className="finance-header">
        <div><span className="section-eyebrow">FINANCEIRO</span><h1>Faturas e recebimentos</h1><p>Acompanhe cobranças geradas pela operação, saldo em aberto e recebimentos PIX.</p></div>
        <Link className="primary-action" href="/">Voltar para a operação</Link>
      </header>

      <section className="finance-summary" aria-label="Resumo financeiro">
        <article className="pulse-card"><span className="section-eyebrow">EM ABERTO</span><div className="pulse-number"><strong>{openInvoices.length}</strong><span>faturas</span></div></article>
        <article className="pulse-card"><span className="section-eyebrow">A RECEBER</span><div className="pulse-number"><strong>{money(String(receivable), "BRL")}</strong></div></article>
        <article className="pulse-card"><span className="section-eyebrow">TOTAL</span><div className="pulse-number"><strong>{invoices.length}</strong><span>faturas</span></div></article>
      </section>

      {billingPending ? (
        <section className="quiet-state" aria-live="polite">
          <div><strong>Uso finalizado. Cobrança em processamento.</strong><span>O financeiro será atualizado após o processamento do evento de conclusão do uso.</span></div>
          <Link className="text-action" href={`/financeiro?usage=${encodeURIComponent(requestedUsageId)}`}>Atualizar financeiro</Link>
        </section>
      ) : null}

      {error ? <section className="operational-empty"><strong>{error}</strong></section> : invoices.length === 0 && !billingPending ? (
        <section className="quiet-state"><div><strong>Nenhuma fatura encontrada</strong><span>As cobranças geradas pela operação aparecerão aqui.</span></div></section>
      ) : invoices.length > 0 ? (
        <section className="finance-list">
          {sortedInvoices.map((invoice) => {
            const detail = details.get(invoice.id);
            const canReceive = invoice.status === "OPEN" || invoice.status === "PARTIALLY_PAID";
            const canClose = canReceive && invoice.source_usage_id === null && !invoice.manual_closed_at;
            const professionalName = professionalById.get(invoice.professional_id)?.name ?? "Profissional";
            const selected = invoiceContainsUsage(invoice, detail, requestedUsageId);
            return (
              <article className="finance-card" data-selected={selected || undefined} key={invoice.id}>
                <div className="finance-card-heading"><div><span className="section-eyebrow">{selected ? "COBRANÇA DO USO FINALIZADO" : "FATURA"}</span><strong>{professionalName}</strong></div><span className={`status-pill status-${invoice.status === "PAID" ? "positive" : "attention"}`}>{statusLabel(invoice.status)}</span></div>
                <div className="finance-amount"><span>Total</span><strong>{money(invoice.total_amount, invoice.currency)}</strong></div>
                <div className="finance-meta">
                  <span>Recebido: {money(detail?.confirmed_amount ?? "0", invoice.currency)}</span>
                  <span>Saldo: {money(detail?.remaining_amount ?? invoice.total_amount, invoice.currency)}</span>
                  <span>Criada em {new Intl.DateTimeFormat("pt-BR").format(new Date(invoice.created_at))}</span>
                </div>
                {detail && detail.items.length > 0 ? <div className="finance-list" aria-label={`Composição da fatura de ${professionalName}`}>{detail.items.map((item) => <div className="finance-meta" key={item.id}><span>{item.description}</span><strong>{money(item.total_amount, invoice.currency)}</strong></div>)}</div> : null}
                {canReceive ? <form action={confirmPixAction} className="finance-payment-form"><input name="invoice_id" type="hidden" value={invoice.id} /><label><span>Valor recebido via PIX</span><input inputMode="decimal" name="amount" placeholder="0,00" required type="number" min="0.01" step="0.01" /></label><label><span>Referência</span><input name="reference" placeholder="Comprovante ou observação" /></label><button className="primary-action" type="submit">Confirmar PIX</button></form> : null}
                {canClose ? <form action={closeInvoiceAction}><input name="invoice_id" type="hidden" value={invoice.id} /><button className="text-action" type="submit">Encerrar fatura manual</button></form> : null}
              </article>
            );
          })}
        </section>
      ) : null}
    </main>
  );
}
