import { BcosShell } from "../../components/bcos-shell";
import { requireTenantRole } from "../../lib/auth/authorization";

export const dynamic = "force-dynamic";

export default async function AdministrationLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const tenant = await requireTenantRole(["OWNER", "ADMIN"]);
  return <BcosShell tenant={tenant} active="administracao">{children}</BcosShell>;
}
