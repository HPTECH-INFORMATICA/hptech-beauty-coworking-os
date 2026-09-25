import { requireTenantRole } from "../../lib/auth/authorization";
export const dynamic = "force-dynamic";
export default async function OperationLayout({ children }: Readonly<{ children: React.ReactNode }>) { await requireTenantRole(["OWNER", "ADMIN", "RECEPTION"]); return children; }
