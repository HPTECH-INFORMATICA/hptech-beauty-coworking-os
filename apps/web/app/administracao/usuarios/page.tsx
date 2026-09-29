import Link from "next/link";

import { getTenantMemberships } from "../../../lib/bcos-api";
import { inviteUserAction, updateUserStatusAction } from "./actions";

export const dynamic = "force-dynamic";

const roleLabel = { OWNER: "Proprietário", ADMIN: "Administrador", RECEPTION: "Recepção", PROFESSIONAL: "Profissional" } as const;
const statusLabel = { INVITED: "Convidado", ACTIVE: "Ativo", INACTIVE: "Inativo" } as const;

export default async function UsersAdminPage({ searchParams }: { searchParams: Promise<{ invited?: string }> }) {
  const [{ invited }, memberships] = await Promise.all([searchParams, getTenantMemberships()]);

  return <main className="admin-page">
    <header className="admin-page-head">
      <div>
        <span>Administração / Usuários</span>
        <h1>Usuários e acessos</h1>
        <p>Administre quem pode acessar o coworking e qual papel cada pessoa exerce.</p>
      </div>
      <nav className="admin-section-nav" aria-label="Administração de usuários">
        <Link href="/administracao">Configurações</Link>
        <Link className="active" href="/administracao/usuarios">Usuários</Link>
      </nav>
    </header>

    {invited ? <div className="platform-success"><strong>Convite registrado</strong><span>O acesso permanece pendente até a identidade confiável ser ativada.</span></div> : null}

    <section className="tenant-user-layout">
      <div className="tenant-user-list">
        {memberships.map((item) => <article key={item.id} className="tenant-user-card">
          <div>
            <span>{roleLabel[item.role]}</span>
            <strong>{item.external_user_id}</strong>
            <small>{statusLabel[item.status]}</small>
          </div>
          {item.role !== "OWNER" ? <form action={updateUserStatusAction}>
            <input type="hidden" name="membership_id" value={item.id} />
            <select name="status" defaultValue={item.status === "INVITED" ? "ACTIVE" : item.status} aria-label={`Situação de ${item.external_user_id}`}>
              <option value="ACTIVE">Ativo</option>
              <option value="INACTIVE">Inativo</option>
            </select>
            <button type="submit">Atualizar acesso</button>
          </form> : <span className="tenant-owner-lock">Acesso do proprietário</span>}
        </article>)}
        {!memberships.length ? <div className="access-empty"><strong>Nenhum usuário adicional cadastrado</strong><span>Convide a equipe quando estiver pronta para operar o coworking.</span></div> : null}
      </div>

      <aside className="tenant-invite-card">
        <span>NOVO ACESSO</span>
        <h2>Convidar usuário</h2>
        <p>Informe a identidade confiável e defina o papel. O convite não ativa o acesso automaticamente.</p>
        <form action={inviteUserAction}>
          <label>Identidade externa<input name="external_user_id" required placeholder="ID da identidade confiável" /></label>
          <label>Papel<select name="role" defaultValue="RECEPTION"><option value="ADMIN">Administrador</option><option value="RECEPTION">Recepção</option><option value="PROFESSIONAL">Profissional</option></select></label>
          <button type="submit">Criar convite</button>
        </form>
      </aside>
    </section>
  </main>;
}
