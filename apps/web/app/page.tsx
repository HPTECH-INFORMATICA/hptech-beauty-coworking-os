import {
  getBookings,
  getProfessionals,
  getResources,
  getUnits,
  type Booking,
  type Professional,
  type Resource,
} from "../lib/bcos-api";

export const dynamic = "force-dynamic";

type DashboardData = {
  unitName: string;
  timezone: string;
  resources: Resource[];
  professionals: Professional[];
  bookings: Booking[];
  error: string | null;
};

function dateKey(date: Date, timeZone: string): string {
  const parts = new Intl.DateTimeFormat("en", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);

  const year = parts.find((part) => part.type === "year")?.value ?? "";
  const month = parts.find((part) => part.type === "month")?.value ?? "";
  const day = parts.find((part) => part.type === "day")?.value ?? "";

  return `${year}-${month}-${day}`;
}

function formatTime(value: string, timeZone: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone,
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatDay(timeZone: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone,
    weekday: "long",
    day: "2-digit",
    month: "long",
  }).format(new Date());
}

function normalizeStatus(value: string): string {
  const status = value.toUpperCase();

  const dictionary: Record<string, string> = {
    ACTIVE: "Ativo",
    AVAILABLE: "Livre",
    FREE: "Livre",
    LIVRE: "Livre",
    RESERVED: "Reservado",
    CONFIRMED: "Confirmado",
    PENDING: "Pendente",
    CHECKED_IN: "Em atendimento",
    COMPLETED: "Concluído",
    CANCELLED: "Cancelado",
    CLEANING: "Limpeza",
    MAINTENANCE: "Manutenção",
    BLOCKED: "Bloqueado",
    OCUPADO: "Em uso",
    OCCUPIED: "Em uso",
  };

  return dictionary[status] ?? value.replaceAll("_", " ");
}

function statusTone(value: string): string {
  const status = value.toUpperCase();

  if (
    ["AVAILABLE", "FREE", "LIVRE", "ACTIVE", "COMPLETED", "CONFIRMED"].includes(
      status,
    )
  ) {
    return "positive";
  }

  if (["PENDING", "RESERVED", "CLEANING"].includes(status)) {
    return "attention";
  }

  if (["CHECKED_IN", "OCCUPIED", "OCUPADO"].includes(status)) {
    return "live";
  }

  if (["CANCELLED", "BLOCKED", "MAINTENANCE"].includes(status)) {
    return "critical";
  }

  return "neutral";
}

async function loadDashboardData(): Promise<DashboardData> {
  try {
    const units = await getUnits();
    const unit = units.find((item) => item.active) ?? units[0] ?? null;

    const [resources, professionals, bookings] = await Promise.all([
      getResources(unit?.id),
      getProfessionals(),
      getBookings(),
    ]);

    return {
      unitName: unit?.name ?? "Unidade",
      timezone: unit?.timezone ?? "America/Sao_Paulo",
      resources,
      professionals,
      bookings,
      error: null,
    };
  } catch (error) {
    console.error("BCOS operational center load failed:", error);

    return {
      unitName: "Unidade",
      timezone: "America/Sao_Paulo",
      resources: [],
      professionals: [],
      bookings: [],
      error: "Não foi possível carregar a operação neste momento.",
    };
  }
}

function cleanUnitName(name: string): string {
  return name
    .replace(/\s*-\s*homologa[cç][aã]o/gi, "")
    .replace(/\s+homologa[cç][aã]o/gi, "")
    .trim();
}

function ResourceIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M4 20V8.8c0-.7.4-1.4 1-1.7l6-3.3c.6-.3 1.3-.3 1.9 0L19 7.1c.6.4 1 1 1 1.7V20M2 20h20M8 20v-5h8v5M8 10h.01M12 10h.01M16 10h.01" />
    </svg>
  );
}

function PersonIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM4.5 20c.8-3.5 3.3-5.5 7.5-5.5s6.7 2 7.5 5.5" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <circle cx="11" cy="11" r="6.5" />
      <path d="m16 16 4 4" />
    </svg>
  );
}

function CalendarIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <rect x="3" y="5" width="18" height="16" rx="3" />
      <path d="M8 3v4M16 3v4M3 10h18" />
    </svg>
  );
}

function ClockIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  );
}

function ArrowIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M5 12h14M14 7l5 5-5 5" />
    </svg>
  );
}

function resolveCurrentBooking(
  bookings: Booking[],
  now: Date,
): Booking | undefined {
  const nowMs = now.getTime();

  return bookings.find((booking) => {
    const start = new Date(booking.starts_at).getTime();
    const end = new Date(booking.ends_at).getTime();
    const status = booking.status.toUpperCase();

    return (
      !["CANCELLED", "COMPLETED"].includes(status) &&
      start <= nowMs &&
      nowMs <= end
    );
  });
}

export default async function HomePage() {
  const data = await loadDashboardData();
  const unitName = cleanUnitName(data.unitName);
  const now = new Date();
  const today = dateKey(now, data.timezone);

  const todayBookings = data.bookings
    .filter(
      (booking) =>
        dateKey(new Date(booking.starts_at), data.timezone) === today &&
        booking.status.toUpperCase() !== "CANCELLED",
    )
    .sort(
      (left, right) =>
        new Date(left.starts_at).getTime() -
        new Date(right.starts_at).getTime(),
    );

  const currentBooking = resolveCurrentBooking(todayBookings, now);

  const upcomingBookings = todayBookings
    .filter(
      (booking) =>
        new Date(booking.starts_at).getTime() > now.getTime() &&
        booking.status.toUpperCase() !== "COMPLETED",
    )
    .slice(0, 5);

  const completedToday = todayBookings.filter(
    (booking) => booking.status.toUpperCase() === "COMPLETED",
  ).length;

  const resourceById = new Map(
    data.resources.map((resource) => [resource.id, resource]),
  );

  const professionalById = new Map(
    data.professionals.map((professional) => [
      professional.id,
      professional,
    ]),
  );

  const activeResources = data.resources.filter((resource) => resource.active);

  return (
    <main className="product-shell">
      <aside className="product-rail">
        <div className="rail-brand">
          <div className="rail-brand-mark">H</div>
          <div className="rail-brand-copy">
            <strong>HPTECH</strong>
            <span>Beauty Coworking OS</span>
          </div>
        </div>

        <nav className="rail-nav" aria-label="Navegação principal">
          <a className="rail-link rail-link-active" href="#agora">
            <span className="rail-icon">
              <ClockIcon />
            </span>
            <span>Agora</span>
          </a>

          <a className="rail-link" href="#agenda">
            <span className="rail-icon">
              <CalendarIcon />
            </span>
            <span>Agenda</span>
          </a>

          <a className="rail-link" href="#espacos">
            <span className="rail-icon">
              <ResourceIcon />
            </span>
            <span>Espaços</span>
          </a>

          <a className="rail-link" href="#profissionais">
            <span className="rail-icon">
              <PersonIcon />
            </span>
            <span>Profissionais</span>
          </a>
        </nav>

        <div className="rail-bottom">
          <div className="tenant-signature">
            <span className="tenant-logo-placeholder" aria-hidden="true">
              LB
            </span>

            <div>
              <strong>{unitName}</strong>
              <span>Ambiente operacional</span>
            </div>
          </div>

          <div className="powered-by">
            <span>Produto</span>
            <strong>HPTECH PLATFORM</strong>
          </div>
        </div>
      </aside>

      <section className="product-workspace">
        <header className="command-header">
          <div className="command-heading">
            <span>Central da Recepção</span>
            <strong>{unitName}</strong>
          </div>

          <button className="global-command" type="button">
            <span className="global-command-icon">
              <SearchIcon />
            </span>

            <span className="global-command-label">
              Buscar pessoa, reserva ou espaço
            </span>

            <kbd>Ctrl K</kbd>
          </button>

          <div className="operator">
            <div className="operator-copy">
              <strong>Recepção</strong>
              <span>Operação do dia</span>
            </div>

            <div className="operator-avatar">
              <PersonIcon />
            </div>
          </div>
        </header>

        <div className="operational-canvas">
          <section className="day-heading" id="agora">
            <div>
              <span className="day-kicker">{formatDay(data.timezone)}</span>
              <h1>O que está acontecendo agora.</h1>
            </div>

            <div
              className={
                data.error
                  ? "live-health live-health-error"
                  : "live-health"
              }
            >
              <span className="live-health-dot" />
              <div>
                <strong>
                  {data.error ? "Operação indisponível" : "Operação conectada"}
                </strong>
                <span>{data.error ?? `${todayBookings.length} reservas hoje`}</span>
              </div>
            </div>
          </section>

          <section className="now-layout">
            <article className="now-card">
              <div className="section-heading">
                <div>
                  <span className="section-eyebrow">AGORA</span>
                  <h2>Operação em curso</h2>
                </div>

                <span className="section-live-badge">AO VIVO</span>
              </div>

              {data.error ? (
                <div className="operational-empty">
                  <div className="empty-symbol">!</div>
                  <div>
                    <strong>Não foi possível carregar a operação</strong>
                    <p>{data.error}</p>
                  </div>
                </div>
              ) : currentBooking ? (
                <div className="current-operation">
                  <div className="current-time">
                    <span>INÍCIO</span>
                    <strong>
                      {formatTime(currentBooking.starts_at, data.timezone)}
                    </strong>
                  </div>

                  <div className="current-people">
                    <div className="profile-photo profile-photo-placeholder">
                      <PersonIcon />
                    </div>

                    <div className="current-copy">
                      <span className="current-label">Profissional</span>
                      <strong>
                        {professionalById.get(currentBooking.professional_id)
                          ?.name ?? "Profissional"}
                      </strong>

                      <div className="current-meta">
                        <span>
                          {resourceById.get(currentBooking.resource_id)?.name ??
                            "Espaço"}
                        </span>
                        <span className="meta-separator" />
                        <span>
                          {formatTime(
                            currentBooking.starts_at,
                            data.timezone,
                          )}{" "}
                          –{" "}
                          {formatTime(currentBooking.ends_at, data.timezone)}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="current-action">
                    <span
                      className={`status-pill status-${statusTone(
                        currentBooking.status,
                      )}`}
                    >
                      {normalizeStatus(currentBooking.status)}
                    </span>

                    <button className="primary-action" type="button">
                      <span>Abrir operação</span>
                      <ArrowIcon />
                    </button>
                  </div>
                </div>
              ) : (
                <div className="operational-empty operational-empty-calm">
                  <div className="empty-symbol">
                    <ClockIcon />
                  </div>

                  <div>
                    <strong>Nenhum atendimento em curso agora</strong>
                    <p>
                      O próximo movimento da operação aparecerá aqui
                      automaticamente.
                    </p>
                  </div>
                </div>
              )}
            </article>

            <aside className="pulse-card">
              <span className="section-eyebrow">HOJE</span>

              <div className="pulse-number">
                <strong>{todayBookings.length}</strong>
                <span>reservas</span>
              </div>

              <div className="pulse-row">
                <span>Concluídas</span>
                <strong>{completedToday}</strong>
              </div>

              <div className="pulse-row">
                <span>Próximas</span>
                <strong>{upcomingBookings.length}</strong>
              </div>

              <div className="pulse-row">
                <span>Espaços ativos</span>
                <strong>{activeResources.length}</strong>
              </div>
            </aside>
          </section>

          <section className="agenda-section" id="agenda">
            <div className="section-heading">
              <div>
                <span className="section-eyebrow">PRÓXIMOS</span>
                <h2>O ritmo das próximas horas</h2>
              </div>

              <button className="text-action" type="button">
                <span>Ver agenda completa</span>
                <ArrowIcon />
              </button>
            </div>

            {upcomingBookings.length === 0 ? (
              <div className="quiet-state">
                <div className="quiet-state-icon">
                  <CalendarIcon />
                </div>

                <div>
                  <strong>Nenhuma próxima reserva</strong>
                  <span>A agenda futura do dia está livre.</span>
                </div>
              </div>
            ) : (
              <div className="timeline">
                {upcomingBookings.map((booking, index) => {
                  const professional = professionalById.get(
                    booking.professional_id,
                  );
                  const resource = resourceById.get(booking.resource_id);

                  return (
                    <article className="timeline-item" key={booking.id}>
                      <div className="timeline-hour">
                        <strong>
                          {formatTime(booking.starts_at, data.timezone)}
                        </strong>
                        <span>
                          {formatTime(booking.ends_at, data.timezone)}
                        </span>
                      </div>

                      <div className="timeline-track">
                        <span
                          className={
                            index === 0
                              ? "timeline-dot timeline-dot-next"
                              : "timeline-dot"
                          }
                        />
                      </div>

                      <div className="timeline-content">
                        <div className="profile-photo profile-photo-small">
                          <PersonIcon />
                        </div>

                        <div className="timeline-copy">
                          <strong>{professional?.name ?? "Profissional"}</strong>
                          <span>{resource?.name ?? "Espaço"}</span>
                        </div>

                        <span
                          className={`status-pill status-${statusTone(
                            booking.status,
                          )}`}
                        >
                          {normalizeStatus(booking.status)}
                        </span>

                        <button
                          aria-label="Abrir reserva"
                          className="icon-action"
                          type="button"
                        >
                          <ArrowIcon />
                        </button>
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
          </section>

          <section className="spaces-section" id="espacos">
            <div className="section-heading">
              <div>
                <span className="section-eyebrow">ESPAÇOS</span>
                <h2>O coworking agora</h2>
              </div>

              <span className="section-summary">
                {activeResources.length}{" "}
                {activeResources.length === 1 ? "espaço ativo" : "espaços ativos"}
              </span>
            </div>

            <div className="space-grid">
              {activeResources.map((resource) => {
                const nextBooking = todayBookings.find(
                  (booking) =>
                    booking.resource_id === resource.id &&
                    new Date(booking.starts_at).getTime() > now.getTime() &&
                    booking.status.toUpperCase() !== "CANCELLED",
                );

                const nextProfessional = nextBooking
                  ? professionalById.get(nextBooking.professional_id)
                  : undefined;

                return (
                  <article className="space-card" key={resource.id}>
                    <div className="space-visual">
                      <div className="space-visual-pattern" />

                      <div className="space-visual-icon">
                        <ResourceIcon />
                      </div>

                      <span
                        className={`space-status status-${statusTone(
                          resource.operational_status,
                        )}`}
                      >
                        <span />
                        {normalizeStatus(resource.operational_status)}
                      </span>
                    </div>

                    <div className="space-body">
                      <div>
                        <span className="space-label">ESPAÇO</span>
                        <h3>{resource.name}</h3>
                      </div>

                      {nextBooking ? (
                        <div className="next-occupancy">
                          <span>Próxima ocupação</span>
                          <strong>
                            {formatTime(nextBooking.starts_at, data.timezone)}
                          </strong>
                          <small>
                            {nextProfessional?.name ?? "Profissional"}
                          </small>
                        </div>
                      ) : (
                        <div className="next-occupancy">
                          <span>Próxima ocupação</span>
                          <strong>Sem reserva</strong>
                          <small>Agenda livre</small>
                        </div>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
          </section>

          <section className="people-section" id="profissionais">
            <div className="section-heading">
              <div>
                <span className="section-eyebrow">PROFISSIONAIS</span>
                <h2>Pessoas que movimentam a operação</h2>
              </div>

              <span className="section-summary">
                {data.professionals.length} cadastrados
              </span>
            </div>

            <div className="people-grid">
              {data.professionals.map((professional) => {
                const nextBooking = upcomingBookings.find(
                  (booking) =>
                    booking.professional_id === professional.id,
                );

                return (
                  <article className="person-card" key={professional.id}>
                    <div className="person-photo">
                      <PersonIcon />

                      <span
                        className={`person-presence status-${statusTone(
                          professional.status,
                        )}`}
                      />
                    </div>

                    <div className="person-info">
                      <strong>{professional.name}</strong>

                      <span>
                        {professional.email ??
                          professional.phone ??
                          "Contato não informado"}
                      </span>

                      {nextBooking ? (
                        <div className="person-next">
                          <span>Próxima reserva</span>
                          <strong>
                            {formatTime(
                              nextBooking.starts_at,
                              data.timezone,
                            )}{" "}
                            ·{" "}
                            {resourceById.get(nextBooking.resource_id)?.name ??
                              "Espaço"}
                          </strong>
                        </div>
                      ) : (
                        <div className="person-next">
                          <span>Próxima reserva</span>
                          <strong>Sem compromisso próximo</strong>
                        </div>
                      )}
                    </div>

                    <button
                      aria-label={`Abrir ${professional.name}`}
                      className="icon-action"
                      type="button"
                    >
                      <ArrowIcon />
                    </button>
                  </article>
                );
              })}
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}