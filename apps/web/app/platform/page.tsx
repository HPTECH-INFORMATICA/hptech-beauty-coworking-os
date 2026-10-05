import Link from "next/link";

import { getContractingTenants } from "../../lib/bcos-api";

export const dynamic = "force-dynamic";

export default async function PlatformPage() {
  const clients = await getContractingTenants();
  const active = clients.filter((client) => client.status === "ACTIVE").length;
  const pending = clients.filter((client) => client.status === "PENDING_ACTIVATION").length;
  const suspended = clients.filter((client) => client.status === "SUSPENDED").length;
  const awaitingOwner = clients.filter(
    (client) => client.owner_membership_status !== "ACTIVE",
  );

  return (
    <main className="platform-shell">
      <aside className="platform-rail">
        <div>
          <div className="platform-brand"><span>H</span><div><strong>HPTECH</strong><small>Administração BCOS</small></div></div>
          <nav>
            <Link className="active" href="/platform">Visão geral</Link>
            <Link href="/platform/clientes">Clientes</Link>
          </nav>
        </div>
        <div className="platform-rail-foot"><small>CONSOLE DA CONTRATADA</small><strong>HPTECH PLATFORM</strong></div>
      </aside>
      <section className="platform-workspace">
        <header className="platform-header">
          <div><span>HPTECH / PLATAFORMA</span><strong>Controle dos contratantes</strong></div>
          <Link className="platform-primary" href="/platform/clientes/novo">Cadastrar cliente</Link>
        </header>
        <div className="platform-canvas">
          <div className="platform-title">
            <span>VISÃO GERAL</span>
            <h1>Operação comercial do BCOS.</h1>
            <p>Acompanhe contratação, acesso do proprietário e situação comercial sem entrar na administração interna do cliente.</p>
          </div>
          <div className="platform-detail-grid">
            <section className="platform-detail-card"><span>CONTRATANTES</span><strong>{clients.length}</strong><p>Total cadastrado no BCOS.</p></section>
            <section className="platform-detail-card"><span>ATIVOS</span><strong>{active}</strong><p>Ambientes comercialmente liberados.</p></section>
            <section className="platform-detail-card"><span>PENDENTES</span><strong>{pending}</strong><p>Aguardando conclusão do ciclo de ativação.</p></section>
            <section className="platform-detail-card"><span>SUSPENSOS</span><strong>{suspended}</strong><p>Contratantes com operação suspensa.</p></section>
          </div>
          <section className="platform-client-list">
            <div className="platform-title"><span>ATENÇÃO</span><h2>Acesso do proprietário</h2><p>Contratantes cujo primeiro OWNER ainda não concluiu o aceite.</p></div>
            {awaitingOwner.slice(0, 6).map((client) => (
              <Link key={client.id} href={`/platform/clientes/${client.id}`} className="platform-client-row">
                <div><strong>{client.trade_name}</strong><span>{client.email}</span></div>
                <div><span className="platform-status platform-status-pending_activation">{client.owner_membership_status === "INVITED" ? "Aguardando aceite" : "Acesso não concluído"}</span><small>Revisar contratante</small></div>
              </Link>
            ))}
            {awaitingOwner.length === 0 ? <div className="platform-empty"><strong>Nenhuma pendência de proprietário</strong><p>Todos os contratantes cadastrados concluíram esta etapa de acesso.</p></div> : null}
          </section>
        </div>
      </section>
    </main>
  );
}
