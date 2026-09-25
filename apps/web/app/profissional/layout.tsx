import { requireTenantRole } from "../../lib/auth/authorization";

export const dynamic = "force-dynamic";

export default async function ProfessionalLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  await requireTenantRole(["PROFESSIONAL"]);
  return children;
}
