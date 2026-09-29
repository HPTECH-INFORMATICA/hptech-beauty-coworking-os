import { SessionControls } from "../../components/session-controls";
import { auth } from "../../lib/auth/server";
import { requireTenantRole } from "../../lib/auth/authorization";

export const dynamic = "force-dynamic";

const roleLabel = {
  OWNER: "Proprietário",
  ADMIN: "Administrador",
  RECEPTION: "Recepção",
  PROFESSIONAL: "Profissional",
} as const;

export default async function AdministrationLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const [tenant, sessionResult] = await Promise.all([
    requireTenantRole(["OWNER", "ADMIN"]),
    auth.getSession(),
  ]);
  const user = sessionResult.data?.user;
  const identity = user?.name || user?.email || "Usuário autenticado";

  return (
    <div className="tenant-authenticated-shell">
      <div className="tenant-context">
        <div className="tenant-context-copy">
          <span>{tenant.tenant_name}</span>
          <strong>{roleLabel[tenant.role]} · Administração</strong>
        </div>
        <SessionControls label={identity} />
      </div>
      {children}
    </div>
  );
}
