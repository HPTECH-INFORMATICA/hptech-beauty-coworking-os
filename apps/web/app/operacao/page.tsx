import Link from "next/link";

import { checkOutAction } from "../operations/actions";

export const dynamic = "force-dynamic";

type OperationPageProps = {
  searchParams: Promise<{ usage?: string }>;
};

export default async function OperationPage({ searchParams }: OperationPageProps) {
  const { usage } = await searchParams;

  return (
    <main className="finance-shell">
      <header className="finance-header">
        <div>
          <span className="section-eyebrow">OPERAÇÃO EM CURSO</span>
          <h1>Uso real do espaço</h1>
          <p>
            O check-in foi registrado. Finalize o uso para disparar o processamento
            operacional e financeiro correspondente.
          </p>
        </div>
        <Link className="text-action" href="/">
          Voltar para a central
        </Link>
      </header>

      {usage ? (
        <section className="now-card">
          <div className="section-heading">
            <div>
              <span className="section-eyebrow">USAGE</span>
              <h2>Atendimento em andamento</h2>
            </div>
            <span className="section-live-badge">AO VIVO</span>
          </div>

          <div className="current-operation">
            <div className="current-copy">
              <span className="current-label">Identificador do uso</span>
              <strong>{usage}</strong>
              <div className="current-meta">
                <span>Ocupação real registrada pelo BCOS</span>
              </div>
            </div>

            <form action={checkOutAction} className="current-action">
              <input name="usage_id" type="hidden" value={usage} />
              <button className="primary-action" type="submit">
                Finalizar uso / Check-out
              </button>
            </form>
          </div>
        </section>
      ) : (
        <section className="operational-empty">
          <div>
            <strong>Nenhum uso foi informado.</strong>
            <p>Inicie o atendimento pela reserva na Central da Recepção.</p>
          </div>
        </section>
      )}
    </main>
  );
}
