import Link from "next/link";

import {
  getProfessionals,
  getReceptionAgenda,
  getResources,
  getUnits,
  type AgendaEntry,
  type Professional,
  type Resource,
} from "../../lib/bcos-api";
import { checkOutAction } from "../operations/actions";

export const dynamic = "force-dynamic";

type OperationPageProps = {
  searchParams: Promise<{ usage?: string }>;
};

function formatDateTime(value: string, timeZone: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone,
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

export default async function OperationPage({ searchParams }: OperationPageProps) {
  const { usage } = await searchParams;
  let entry: AgendaEntry | null = null;
  let professional: Professional | null = null;
  let resource: Resource | null = null;
  let timezone = "America/Sao_Paulo";
  let error: string | null = null;

  if (usage) {
    try {
      const units = await getUnits();
      const unit = units.find((item) => item.active) ?? units[0];
      if (unit) {
        timezone = unit.timezone;
        const now = new Date();
        const past = new Date(now);
        past.setDate(past.getDate() - 30);
        const future = new Date(now);
        future.setDate(future.getDate() + 90);
        const [agenda, professionals, resources] = await Promise.all([
          getReceptionAgenda({
            unitId: unit.id,
            startsAt: past.toISOString(),
            endsAt: future.toISOString(),
          }),
          getProfessionals(),
          getResources(unit.id),
        ]);
        entry = agenda.find((item) => item.usage?.id === usage) ?? null;
        if (entry?.usage) {
          professional =
            professionals.find((item) => item.id === entry?.usage?.professional_id) ?? null;
          resource = resources.find((item) => item.id === entry?.usage?.resource_id) ?? null;
        }
      }
    } catch (caught) {
      console.error("BCOS operation workspace load failed:", caught);
      error = "Não foi possível carregar os detalhes do atendimento neste momento.";
    }
  }

  const activeUsage = entry?.usage?.status.toUpperCase() === "CHECKED_IN" ? entry.usage : null;

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
          <Link href="/check-in">Check-in</Link>
          <Link href="/financeiro">Financeiro</Link>
        </nav>
      </header>

      <div className="agenda-canvas operation-canvas">
        <section className="agenda-hero">
          <div>
            <span className="section-eyebrow">OPERAÇÃO • USO REAL</span>
            <h1>Atendimento em curso</h1>
            <p>Acompanhe a ocupação iniciada e finalize o uso quando o espaço for liberado.</p>
          </div>
          <div className="agenda-hero-actions">
            <Link className="text-action" href="/agenda">Ver agenda</Link>
            <Link className="primary-action" href="/">Voltar para a central</Link>
          </div>
        </section>

        {error ? (
          <section className="operational-empty operation-empty"><strong>{error}</strong></section>
        ) : activeUsage && entry ? (
          <>
            <section className="operation-kpis">
              <div className="agenda-kpi">
                <span>STATUS</span>
                <strong className="operation-live-text">Em atendimento</strong>
              </div>
              <div className="agenda-kpi">
                <span>ESPAÇO</span>
                <strong>{resource?.name ?? "Espaço"}</strong>
              </div>
              <div className="operation-guidance">
                <span className="section-eyebrow">FLUXO OPERACIONAL</span>
                <strong>Check-in → Uso real → Check-out → Billing</strong>
                <p>O check-out encerra o uso operacional e mantém o processamento financeiro sob autoridade do domínio.</p>
              </div>
            </section>

            <section className="operation-board">
              <header className="operation-board-head">
                <div>
                  <span className="section-eyebrow">ATENDIMENTO ATUAL</span>
                  <h2>{professional?.name ?? "Profissional"}</h2>
                </div>
                <span className="section-live-badge">AO VIVO</span>
              </header>

              <div className="operation-body">
                <div className="operation-resource">
                  <span className="section-eyebrow">OCUPAÇÃO</span>
                  <strong>{resource?.name ?? "Espaço"}</strong>
                  <span>{professional?.name ?? "Profissional"}</span>
                </div>

                <div className="operation-timeline">
                  <div>
                    <span>RESERVA</span>
                    <strong>{formatDateTime(entry.booking.starts_at, timezone)}</strong>
                    <small>até {formatDateTime(entry.booking.ends_at, timezone)}</small>
                  </div>
                  <div>
                    <span>CHECK-IN</span>
                    <strong>
                      {activeUsage.checked_in_at
                        ? formatDateTime(activeUsage.checked_in_at, timezone)
                        : "Registrado"}
                    </strong>
                    <small>uso real iniciado</small>
                  </div>
                </div>

                <form action={checkOutAction} className="operation-checkout">
                  <input name="usage_id" type="hidden" value={activeUsage.id} />
                  <div>
                    <span className="status-pill status-live">Em atendimento</span>
                    <p>Finalize somente quando o profissional liberar o espaço.</p>
                  </div>
                  <button className="primary-action" type="submit">
                    Finalizar uso / Check-out
                  </button>
                </form>
              </div>
            </section>
          </>
        ) : usage ? (
          <section className="operation-empty">
            <span className="section-eyebrow">SEM USO ATIVO</span>
            <strong>Atendimento em curso não encontrado.</strong>
            <p>Volte para a Central da Recepção e abra uma ocupação que esteja com check-in ativo.</p>
            <Link className="primary-action" href="/">Voltar para a central</Link>
          </section>
        ) : (
          <section className="operation-empty">
            <span className="section-eyebrow">AGUARDANDO ATENDIMENTO</span>
            <strong>Nenhum uso foi informado.</strong>
            <p>Inicie o atendimento a partir de uma reserva confirmada.</p>
            <Link className="primary-action" href="/check-in">Ir para check-in</Link>
          </section>
        )}
      </div>
    </main>
  );
}
