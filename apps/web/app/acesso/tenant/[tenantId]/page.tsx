import { redirect } from "next/navigation";

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

  // Tenant selection must persist the tenant cookie from a Route Handler.
  // Next.js does not allow mutating cookies from a Server Component.
  redirect(`/acesso/selecionar/${encodeURIComponent(tenantId)}`);
}
