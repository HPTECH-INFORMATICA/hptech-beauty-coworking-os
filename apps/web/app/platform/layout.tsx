import { redirect } from "next/navigation";

import { getAccessResolution } from "../../lib/bcos-api";
import { auth } from "../../lib/auth/server";
import { SessionControls } from "../../components/session-controls";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function PlatformLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const { data: session } = await auth.getSession();
  if (!session?.user) {
    redirect("/auth/sign-in");
  }

  try {
    const access = await getAccessResolution();
    if (access.platform_destination !== "/platform") {
      redirect("/acesso");
    }
  } catch (error) {
    console.error(
      "BCOS platform authorization gate failed:",
      error instanceof Error ? error.message : "unknown error",
    );
    redirect("/acesso");
  }

  const identityLabel = session.user.name || session.user.email || "Usuário autenticado";

  return <><div className="platform-session"><SessionControls label={identityLabel} /></div>{children}</>;
}
