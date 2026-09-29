import { BcosShell } from "../../components/bcos-shell";
import { requireTenantRole } from "../../lib/auth/authorization";

export const dynamic = "force-dynamic";

export default async function ModuleLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const tenant = await requireTenantRole(["OWNER","ADMIN","RECEPTION"]);
  return <BcosShell tenant={tenant} active="agenda">{children}</BcosShell>;
}
