import { NextResponse } from "next/server";

import { persistSelectedTenant } from "../../../../lib/bcos-api";
import { auth } from "../../../../lib/auth/server";

export const dynamic = "force-dynamic";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ tenantId: string }> },
) {
  const { data: session } = await auth.getSession();
  if (!session?.user) {
    return NextResponse.redirect(new URL("/auth/sign-in", request.url));
  }

  const { tenantId } = await params;

  try {
    const selected = await persistSelectedTenant(tenantId);
    return NextResponse.redirect(new URL(selected.destination, request.url));
  } catch (error) {
    console.error(
      "BCOS tenant selection failed:",
      error instanceof Error ? error.message : "unknown error",
    );
    return NextResponse.redirect(new URL("/acesso?selectionError=1", request.url));
  }
}
