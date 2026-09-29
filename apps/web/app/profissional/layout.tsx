import Link from "next/link";

import { EnvironmentSwitch } from "../../components/environment-switch";
import { SessionControls } from "../../components/session-controls";
import { auth } from "../../lib/auth/server";
import { requireTenantRole } from "../../lib/auth/authorization";

export const dynamic = "force-dynamic";

export default async function ProfessionalLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const tenant = await requireTenantRole(["PROFESSIONAL"]);
  const { data: session } = await auth.getSession();
  const identity = session?.user?.name || session?.user?.email || "Usuário autenticado";

  return (
    <div className="bcos-shell professional-shell">
      <aside className="bcos-sidebar">
        <div>
          <div className="platform-brand"><span>C</span><div><strong>BCOS</strong><small>{tenant.tenant_name}</small></div></div>
          <nav className="bcos-nav" aria-label="Navegação do profissional">
            <Link className="active" href="/profissional">Meu portal</Link>
          </nav>
        </div>
        <div className="bcos-sidebar-foot"><span>Profissional</span><strong>{identity}</strong><span>Produto HPTECH PLATFORM</span></div>
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
