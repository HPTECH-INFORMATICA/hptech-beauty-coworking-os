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
  const can = (permission: AccessTenant["permissions"][number]) => tenant.permissions.includes(permission);
  const canAdminister = can("ADMIN_CONFIG") || can("USER_ADMIN");

  return (
    <div className="bcos-shell">
      <aside className="bcos-sidebar">
        <div>
          <div className="platform-brand">
            <span>C</span>
            <div><strong>BCOS</strong><small>{tenant.tenant_name}</small></div>
          </div>
          <nav className="bcos-nav" aria-label="Navegação principal">
            {can("DASHBOARD_VIEW") ? <Link className={active === "central" ? "active" : ""} href="/">Visão geral</Link> : null}
            {can("AGENDA_VIEW") ? <Link className={active === "agenda" ? "active" : ""} href="/agenda">Agenda</Link> : null}
            {can("AVAILABILITY_VIEW") ? <Link className={active === "disponibilidade" ? "active" : ""} href="/disponibilidade">Disponibilidade</Link> : null}
            {can("CHECKIN_MANAGE") ? <Link className={active === "check-in" ? "active" : ""} href="/check-in">Check-in e uso</Link> : null}
            {can("FINANCE_VIEW") ? <Link className={active === "financeiro" ? "active" : ""} href="/financeiro">Financeiro</Link> : null}
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
