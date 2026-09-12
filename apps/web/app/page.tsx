const resources = [
  {
    name: "Sala 01",
    category: "Estética",
    status: "Livre",
    statusClass: "success",
  },
  {
    name: "Sala 02",
    category: "Estética",
    status: "Livre",
    statusClass: "success",
  },
  {
    name: "Sala 03",
    category: "Estética",
    status: "Livre",
    statusClass: "success",
  },
  {
    name: "Sala 04",
    category: "Estética",
    status: "Livre",
    statusClass: "success",
  },
];

const navigation = [
  "Visão geral",
  "Agenda",
  "Reservas",
  "Recursos",
  "Profissionais",
  "Financeiro",
];

export default function HomePage() {
  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div>
          <div className="brand">
            <div className="brand-mark">H</div>

            <div>
              <strong>HPTECH</strong>
              <span>Beauty Coworking OS</span>
            </div>
          </div>

          <nav className="navigation" aria-label="Navegação principal">
            {navigation.map((item, index) => (
              <button
                className={index === 0 ? "nav-item active" : "nav-item"}
                key={item}
                type="button"
              >
                <span className="nav-dot" />
                {item}
              </button>
            ))}
          </nav>
        </div>

        <div className="sidebar-footer">
          <span className="environment-dot" />
          <div>
            <strong>Ambiente operacional</strong>
            <span>BCOS</span>
          </div>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <span className="eyebrow">Central da Recepção</span>
            <h1>Visão geral</h1>
          </div>

          <div className="topbar-actions">
            <span className="date-badge">Operação do dia</span>

            <div className="avatar" aria-label="Perfil da recepção">
              R
            </div>
          </div>
        </header>

        <div className="content">
          <section className="welcome">
            <div>
              <span className="section-label">Coworking</span>
              <h2>Controle da operação em um só lugar.</h2>
              <p>
                Acompanhe reservas, ocupação dos espaços, uso real,
                faturamento e recebimentos.
              </p>
            </div>

            <div className="system-status">
              <span className="status-indicator" />
              <div>
                <strong>Estrutura operacional pronta</strong>
                <span>Integração com dados reais em andamento</span>
              </div>
            </div>
          </section>

          <section className="metrics" aria-label="Indicadores operacionais">
            <article className="metric-card">
              <span className="metric-label">Reservas hoje</span>
              <strong>—</strong>
              <span className="metric-note">
                Aguardando integração da agenda
              </span>
            </article>

            <article className="metric-card">
              <span className="metric-label">Em atendimento</span>
              <strong>—</strong>
              <span className="metric-note">
                Check-in e uso real
              </span>
            </article>

            <article className="metric-card">
              <span className="metric-label">A receber</span>
              <strong>—</strong>
              <span className="metric-note">
                Faturas abertas
              </span>
            </article>

            <article className="metric-card">
              <span className="metric-label">Recebido via PIX</span>
              <strong>—</strong>
              <span className="metric-note">
                Pagamentos confirmados
              </span>
            </article>
          </section>

          <div className="dashboard-grid">
            <section className="panel operational-panel">
              <div className="panel-header">
                <div>
                  <span className="section-label">Operação</span>
                  <h3>Agenda e uso real</h3>
                </div>

                <span className="panel-badge">Hoje</span>
              </div>

              <div className="empty-state">
                <div className="empty-icon">01</div>

                <div>
                  <strong>Agenda pronta para integração</strong>
                  <p>
                    A próxima integração trará as reservas reais e permitirá
                    acompanhar check-in, uso e check-out.
                  </p>
                </div>
              </div>
            </section>

            <section className="panel finance-panel">
              <div className="panel-header">
                <div>
                  <span className="section-label">Financeiro</span>
                  <h3>Faturamento</h3>
                </div>

                <span className="panel-badge neutral">PIX</span>
              </div>

              <div className="financial-flow">
                <div className="flow-step">
                  <span>1</span>
                  <div>
                    <strong>Uso concluído</strong>
                    <small>Check-out operacional</small>
                  </div>
                </div>

                <div className="flow-line" />

                <div className="flow-step">
                  <span>2</span>
                  <div>
                    <strong>Fatura</strong>
                    <small>Base + excedente</small>
                  </div>
                </div>

                <div className="flow-line" />

                <div className="flow-step">
                  <span>3</span>
                  <div>
                    <strong>PIX</strong>
                    <small>Recebimento confirmado</small>
                  </div>
                </div>
              </div>

              <div className="proof-card">
                <span className="proof-icon">✓</span>

                <div>
                  <strong>Fluxo financeiro validado</strong>
                  <p>
                    O backend já processa faturamento e confirmação de
                    recebimento PIX.
                  </p>
                </div>
              </div>
            </section>
          </div>

          <section className="panel">
            <div className="panel-header">
              <div>
                <span className="section-label">Espaços</span>
                <h3>Recursos do coworking</h3>
              </div>

              <span className="panel-badge">Visão operacional</span>
            </div>

            <div className="resource-grid">
              {resources.map((resource) => (
                <article className="resource-card" key={resource.name}>
                  <div className="resource-number">
                    {resource.name.replace("Sala ", "")}
                  </div>

                  <div className="resource-info">
                    <strong>{resource.name}</strong>
                    <span>{resource.category}</span>
                  </div>

                  <span className={`resource-status ${resource.statusClass}`}>
                    {resource.status}
                  </span>
                </article>
              ))}
            </div>

            <p className="data-notice">
              A disponibilidade exibida nesta primeira superfície ainda não
              representa o estado persistido do banco. A integração real será
              aplicada no próximo passo.
            </p>
          </section>
        </div>
      </section>
    </main>
  );
}