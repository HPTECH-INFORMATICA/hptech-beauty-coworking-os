import Link from "next/link";

import { auth } from "../lib/auth/server";
import type { AccessTenant } from "../lib/bcos-api";
import { EnvironmentSwitch } from "./environment-switch";
import { SessionControls } from "./session-controls";

const roleLabel = {
  OWNER: "Proprietário",
  ADMIN: "Administrador",
  RECEPTION: "Recepção",
  PROFESSIONAL: "Profissional",
} as const;

export async function BcosShell({
  tenant,
  active,
  children,
}: Readonly<{
  tenant: AccessTenant;
  active: "central" | "agenda" | "disponibilidade" | "check-in" | "financeiro" | "administracao";
  children: React.ReactNode;
}>) {
  const { data: session } = await auth.getSession();
  const identity = session?.user?.name || session?.user?.email || "Usuário autenticado";
  const canAdminister = tenant.role === "OWNER" || tenant.role === "ADMIN";

  return (
    <div className="bcos-shell">
      <aside className="bcos-sidebar">
        <div>
          <div className="platform-brand">
            <span>C</span>
            <div><strong>BCOS</strong><small>{tenant.tenant_name}</small></div>
          </div>
          <nav className="bcos-nav" aria-label="Navegação principal">
            <Link className={active === "central" ? "active" : ""} href="/">Visão geral</Link>
            <Link className={active === "agenda" ? "active" : ""} href="/agenda">Agenda</Link>
            <Link className={active === "disponibilidade" ? "active" : ""} href="/disponibilidade">Disponibilidade</Link>
            <Link className={active === "check-in" ? "active" : ""} href="/check-in">Check-in e uso</Link>
            <Link className={active === "financeiro" ? "active" : ""} href="/financeiro">Financeiro</Link>
            {canAdminister ? <Link className={active === "administracao" ? "active" : ""} href="/administracao">Administração</Link> : null}
          </nav>
        </div>
        <div className="bcos-sidebar-foot">
          <span>{roleLabel[tenant.role]}</span>
          <strong>{identity}</strong>
          <span>Produto HPTECH PLATFORM</span>
        </div>
      </aside>
      <div className="bcos-content">
        <header className="bcos-topbar">
          <div><span>Ambiente do cliente</span><strong>{tenant.tenant_name}</strong></div>
          <div className="bcos-session-actions"><EnvironmentSwitch /><SessionControls label={identity} /></div>
        </header>
        {children}
      </div>
    </div>
  );
}
