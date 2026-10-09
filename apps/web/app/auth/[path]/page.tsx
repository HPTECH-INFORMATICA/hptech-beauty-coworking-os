import { AuthView } from "@neondatabase/auth-ui";
import { authViewPaths } from "@neondatabase/auth-ui/server";

export const dynamicParams = false;

export function generateStaticParams() {
  return Object.values(authViewPaths).map((path) => ({ path }));
}

export default async function AuthPage({
  params,
}: {
  params: Promise<{ path: string }>;
}) {
  const { path } = await params;

  return (
    <main className="auth-shell">
      <section className="auth-brand">
        <span>HPTECH PLATFORM</span>
        <h1>Beauty Coworking OS</h1>
        <p>Acesso seguro para administração, recepção e profissionais.</p>
      </section>
      <section className="auth-card">
        <AuthView path={path} />
      </section>
    </main>
  );
}
