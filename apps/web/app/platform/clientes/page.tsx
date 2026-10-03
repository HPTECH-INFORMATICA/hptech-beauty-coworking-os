import Link from "next/link";

import { getContractingTenants } from "../../../lib/bcos-api";

export const dynamic = "force-dynamic";

const labels = { PENDING_ACTIVATION: "Pendente", ACTIVE: "Ativo", SUSPENDED: "Suspenso", INACTIVE: "Inativo" } as const;

export default async function PlatformClientsPage({searchParams}:{searchParams:Promise<{created?:string}>}) {
  const [{created}, clients] = await Promise.all([searchParams, getContractingTenants()]);
  return <main className="platform-shell"><aside className="platform-rail"><div><div className="platform-brand"><span>H</span><div><strong>HPTECH</strong><small>Administração BCOS</small></div></div><nav><Link className="active" href="/platform/clientes">Clientes</Link><Link href="/platform/clientes/novo">Novo cliente</Link></nav></div><div className="platform-rail-foot"><small>CONSOLE DA CONTRATADA</small><strong>HPTECH PLATFORM</strong></div></aside><section className="platform-workspace"><header className="platform-header"><div><span>HPTECH / PLATAFORMA</span><strong>Empresas contratantes</strong></div><Link className="platform-primary" href="/platform/clientes/novo">Cadastrar cliente</Link></header><div className="platform-canvas">{created?<div className="platform-success"><strong>{created}</strong><span>Contratante cadastrado. Primeiro OWNER permanece pendente de ativação.</span></div>:null}<div className="platform-title"><span>CLIENTES BCOS</span><h1>Administração dos contratantes.</h1><p>{clients.length} empresa(s) cadastrada(s) no BCOS.</p></div><section className="platform-client-list">{clients.map(client=><Link key={client.id} href={`/platform/clientes/${client.id}`} className="platform-client-row"><div><strong>{client.trade_name}</strong><span>{client.legal_name} · {client.email}</span></div><div><span className={`platform-status platform-status-${client.status.toLowerCase()}`}>{labels[client.status]}</span><small>{client.slug}</small></div></Link>)}{clients.length===0?<div className="platform-empty"><strong>Nenhum contratante cadastrado</strong><p>Cadastre a primeira empresa para iniciar o onboarding comercial.</p><Link className="platform-primary" href="/platform/clientes/novo">Cadastrar primeiro cliente</Link></div>:null}</section></div></section></main>
}
