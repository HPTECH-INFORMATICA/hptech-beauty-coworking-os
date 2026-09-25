import { requireTenantRole } from "../../lib/auth/authorization";

export const dynamic = "force-dynamic";

export default async function AdministrationLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  await requireTenantRole(["OWNER", "ADMIN"]);
  return children;
}
