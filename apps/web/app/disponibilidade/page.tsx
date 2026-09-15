import Link from "next/link";

import {
  getAvailability,
  getResources,
  getUnits,
  type AvailabilityResponse,
  type Resource,
} from "../../lib/bcos-api";

export const dynamic = "force-dynamic";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

function first(value: string | string[] | undefined): string {
  return typeof value === "string" ? value : "";
}

function localDateTimeInZoneToIso(value: string, timeZone: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value);
  if (!match) throw new Error("Data e hora inválidas.");
  const [, year, month, day, hour, minute] = match;
  const wanted = Date.UTC(Number(year), Number(month) - 1, Number(day), Number(hour), Number(minute));
  let instant = wanted;
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  });
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const parts = Object.fromEntries(formatter.formatToParts(new Date(instant)).map((part) => [part.type, part.value]));
    const represented = Date.UTC(Number(parts.year), Number(parts.month) - 1, Number(parts.day), Number(parts.hour), Number(parts.minute));
    instant += wanted - represented;
  }
  const finalParts = Object.fromEntries(formatter.formatToParts(new Date(instant)).map((part) => [part.type, part.value]));
  const normalized = `${finalParts.year}-${finalParts.month}-${finalParts.day}T${finalParts.hour}:${finalParts.minute}`;
  if (normalized !== value) throw new Error("Horário local inválido para o fuso da unidade.");
  return new Date(instant).toISOString();
}

function bookingHref(resourceId: string, startsAt: string, endsAt: string): string {
  const params = new URLSearchParams({ resource_id: resourceId, starts_at: startsAt, ends_at: endsAt });
  return `/agenda?${params.toString()}`;
}

export default async function AvailabilityPage({ searchParams }: { searchParams: SearchParams }) {
  const query = await searchParams;
  const startsAtLocal = first(query.starts_at);
  const endsAtLocal = first(query.ends_at);
  const resourceId = first(query.resource_id);
  let resources: Resource[] = [];
  let result: AvailabilityResponse | null = null;
  let timezone = "America/Sao_Paulo";
  let unitId = "";
  let error: string | null = null;

  try {
    const units = await getUnits();
    const unit = units.find((item) => item.active) ?? units[0];
    if (unit) {
      unitId = unit.id;
      timezone = unit.timezone;
      resources = (await getResources(unit.id)).filter((item) => item.active);
      if (startsAtLocal && endsAtLocal) {
        const startsAt = localDateTimeInZoneToIso(startsAtLocal, timezone);
        const endsAt = localDateTimeInZoneToIso(endsAtLocal, timezone);
        if (new Date(endsAt).getTime() <= new Date(startsAt).getTime()) throw new Error("O fim deve ser posterior ao início.");
        result = await getAvailability({ unitId, startsAt, endsAt, ...(resourceId ? { resourceId } : {}) });
      }
    }
  } catch (caught) {
    console.error("BCOS availability load failed:", caught);
    error = caught instanceof Error ? caught.message : "Não foi possível consultar a disponibilidade.";
  }

  const resourceById = new Map(resources.map((resource) => [resource.id, resource]));
  return (
    <main className="finance-shell">
      <header className="finance-header">
        <div>
          <span className="section-eyebrow">RECEPÇÃO</span>
          <h1>Disponibilidade de espaços</h1>
          <p>Consulte o período antes de reservar. A resposta vem do contrato canônico de disponibilidade.</p>
        </div>
        <Link className="primary-action" href="/agenda">Voltar para a agenda</Link>
      </header>

      <section className="finance-card">
        <div className="finance-card-heading"><div><span className="section-eyebrow">CONSULTA</span><strong>Período desejado</strong></div></div>
        {unitId ? (
          <form className="finance-list" method="get">
            <label>Início<input className="field" type="datetime-local" name="starts_at" required defaultValue={startsAtLocal} /></label>
            <label>Fim<input className="field" type="datetime-local" name="ends_at" required defaultValue={endsAtLocal} /></label>
            <label>Espaço<select className="field" name="resource_id" defaultValue={resourceId}><option value="">Todos os espaços</option>{resources.map((resource) => <option key={resource.id} value={resource.id}>{resource.name}</option>)}</select></label>
            <button className="primary-action" type="submit">Consultar disponibilidade</button>
          </form>
        ) : <div className="quiet-state"><div><strong>Nenhuma unidade ativa</strong><span>A consulta depende de uma unidade operacional ativa.</span></div></div>}
      </section>

      {error ? <section className="operational-empty"><strong>{error}</strong></section> : null}
      {!error && result ? (
        <section className="finance-list" aria-label="Resultado da disponibilidade">
          {result.resources.length === 0 ? <div className="quiet-state"><div><strong>Nenhum espaço retornado</strong><span>Não há resultado para os filtros informados.</span></div></div> : result.resources.map((item) => (
            <article className="finance-card" key={item.resource_id}>
              <div className="finance-card-heading">
                <div><span className="section-eyebrow">ESPAÇO</span><strong>{resourceById.get(item.resource_id)?.name ?? "Espaço"}</strong></div>
                <span className={`status-pill status-${item.available ? "positive" : "critical"}`}>{item.available ? "Disponível" : "Indisponível"}</span>
              </div>
              {!item.available && item.reason ? <div className="finance-meta"><span>{item.reason}</span></div> : null}
              {item.available ? <Link className="primary-action" href={bookingHref(item.resource_id, startsAtLocal, endsAtLocal)}>Reservar este espaço</Link> : null}
            </article>
          ))}
        </section>
      ) : null}
    </main>
  );
}
