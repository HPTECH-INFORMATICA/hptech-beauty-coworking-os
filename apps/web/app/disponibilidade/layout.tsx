import { BcosShell } from "../../components/bcos-shell";
import { requireTenantPermission } from "../../lib/auth/authorization";

export const dynamic = "force-dynamic";

export default async function ModuleLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const tenant = await requireTenantPermission("AVAILABILITY_VIEW");
  return <BcosShell tenant={tenant} active="disponibilidade">{children}</BcosShell>;
}
