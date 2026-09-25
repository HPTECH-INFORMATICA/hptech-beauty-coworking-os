import { redirect } from "next/navigation";

import { persistSelectedTenant } from "../../../../lib/bcos-api";
import { auth } from "../../../../lib/auth/server";

export const dynamic = "force-dynamic";

export default async function SelectTenantPage({
  params,
}: {
  params: Promise<{ tenantId: string }>;
}) {
  const { data: session } = await auth.getSession();
  if (!session?.user) redirect("/auth/sign-in");

  const { tenantId } = await params;
  try {
    const tenant = await persistSelectedTenant(tenantId);
    redirect(tenant.destination);
  } catch (error) {
    console.error(
      "BCOS tenant selection failed:",
      error instanceof Error ? error.message : "unknown error",
    );
    redirect("/acesso");
  }
}
