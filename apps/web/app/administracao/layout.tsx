import { BcosShell } from "../../components/bcos-shell";
import { requireTenantAnyPermission } from "../../lib/auth/authorization";

export const dynamic = "force-dynamic";

export default async function AdministrationLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const tenant = await requireTenantAnyPermission(["ADMIN_CONFIG","USER_ADMIN"]);
  return <BcosShell tenant={tenant} active="administracao">{children}</BcosShell>;
}
