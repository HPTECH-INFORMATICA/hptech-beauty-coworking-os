import Link from "next/link";
import { notFound } from "next/navigation";

import { getContractingTenant } from "../../../../lib/bcos-api";
import { updateClientStatusAction } from "./actions";

export const dynamic = "force-dynamic";
const labels = { PENDING_ACTIVATION: "Pendente de ativação", ACTIVE: "Ativo", SUSPENDED: "Suspenso", INACTIVE: "Inativo" } as const;

export default async function PlatformClientDetailPage({params}:{params:Promise<{tenantId:string}>}) {
  const {tenantId}=await params;
  let client;
  try { client=await getContractingTenant(tenantId); } catch (error) { if(String(error).includes("HTTP 404")) notFound(); throw error; }
  return <main className="platform-shell"><aside className="platform-rail"><div><div className="platform-brand"><span>H</span><div><strong>HPTECH</strong><small>Administração BCOS</small></div></div><nav><Link className="active" href="/platform/clientes">Clientes</Link><Link href="/platform/clientes/novo">Novo cliente</Link></nav></div></aside><section className="platform-workspace"><header className="platform-header"><div><span>HPTECH / CLIENTE</span><strong>{client.trade_name}</strong></div><Link href="/platform/clientes">Voltar para clientes</Link></header><div className="platform-canvas"><div className="platform-title"><span>CONTRATANTE</span><h1>{client.trade_name}</h1><p>{client.legal_name}</p></div><div className="platform-detail-grid"><section className="platform-detail-card"><span>SITUAÇÃO</span><strong>{labels[client.status]}</strong><p>Slug: {client.slug}</p></section><section className="platform-detail-card"><span>CONTATO</span><strong>{client.email}</strong><p>{client.phone || "Telefone não informado"}</p></section><section className="platform-detail-card"><span>DOCUMENTO</span><strong>{client.tax_id || "Não informado"}</strong><p>Tenant {client.id}</p></section><section className="platform-detail-card"><span>PRIMEIRO OWNER</span><strong>{client.owner_external_user_id}</strong><p>Autoridade de identidade vinculada ao onboarding.</p></section></div><form action={updateClientStatusAction} className="platform-lifecycle"><input type="hidden" name="tenant_id" value={client.id}/><div><span>CICLO DE VIDA</span><strong>Alterar situação do contratante</strong></div><select name="status" defaultValue={client.status}><option value="PENDING_ACTIVATION">Pendente de ativação</option><option value="ACTIVE">Ativo</option><option value="SUSPENDED">Suspenso</option><option value="INACTIVE">Inativo</option></select><button type="submit">Atualizar situação</button></form></div></section></main>
}
