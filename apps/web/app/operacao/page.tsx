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
    <main className="finance-shell">
      <header className="finance-header">
        <div>
          <span className="section-eyebrow">OPERAÇÃO EM CURSO</span>
          <h1>Uso real do espaço</h1>
          <p>Acompanhe o atendimento iniciado e finalize o uso quando o espaço for liberado.</p>
        </div>
        <Link className="text-action" href="/">
          Voltar para a central
        </Link>
      </header>

      {error ? (
        <section className="operational-empty"><strong>{error}</strong></section>
      ) : activeUsage && entry ? (
        <section className="now-card">
          <div className="section-heading">
            <div>
              <span className="section-eyebrow">ATENDIMENTO ATUAL</span>
              <h2>{professional?.name ?? "Profissional"}</h2>
            </div>
            <span className="section-live-badge">AO VIVO</span>
          </div>

          <div className="current-operation">
            <div className="current-copy">
              <span className="current-label">Espaço</span>
              <strong>{resource?.name ?? "Espaço"}</strong>
              <div className="current-meta">
                <span>Reserva: {formatDateTime(entry.booking.starts_at, timezone)} — {formatDateTime(entry.booking.ends_at, timezone)}</span>
                <span>Check-in: {activeUsage.checked_in_at ? formatDateTime(activeUsage.checked_in_at, timezone) : "Registrado"}</span>
              </div>
            </div>

            <form action={checkOutAction} className="current-action">
              <input name="usage_id" type="hidden" value={activeUsage.id} />
              <span className="status-pill status-live">Em atendimento</span>
              <button className="primary-action" type="submit">
                Finalizar uso / Check-out
              </button>
            </form>
          </div>
        </section>
      ) : usage ? (
        <section className="operational-empty">
          <div>
            <strong>Atendimento em curso não encontrado.</strong>
            <p>Volte para a Central da Recepção e abra uma ocupação que esteja com check-in ativo.</p>
          </div>
        </section>
      ) : (
        <section className="operational-empty">
          <div>
            <strong>Nenhum uso foi informado.</strong>
            <p>Inicie o atendimento a partir de uma reserva confirmada.</p>
          </div>
        </section>
      )}
    </main>
  );
}
