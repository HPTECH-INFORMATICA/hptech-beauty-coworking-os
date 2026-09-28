import Link from "next/link";

import { createClientAction } from "./actions";

export const dynamic = "force-dynamic";

export default async function NewPlatformClientPage() {
  return (
    <main className="platform-shell">
      <aside className="platform-rail">
        <div>
          <div className="platform-brand"><span>H</span><div><strong>HPTECH</strong><small>Administração BCOS</small></div></div>
          <nav><Link href="/platform/clientes">Clientes</Link><Link className="active" href="/platform/clientes/novo">Novo cliente</Link></nav>
        </div>
        <div className="platform-rail-foot"><small>CONSOLE DA CONTRATADA</small><strong>HPTECH PLATFORM</strong></div>
      </aside>
      <section className="platform-workspace">
        <header className="platform-header"><div><span>HPTECH / CLIENTES</span><strong>Novo contratante</strong></div><Link href="/platform/clientes">Voltar para clientes</Link></header>
        <div className="platform-canvas">
          <div className="platform-title"><span>ONBOARDING</span><h1>Cadastrar empresa contratante.</h1><p>Cria o cadastro comercial da empresa. O acesso do proprietário pode ser ativado depois, sem recriar o contratante.</p></div>
          <form action={createClientAction} className="platform-form-card">
            <div className="platform-form-section"><div><span>EMPRESA</span><h2>Identificação do contratante</h2></div><div className="platform-fields">
              <label>Nome no sistema<input name="name" required maxLength={160}/></label>
              <label>Identificador (slug)<input name="slug" required maxLength={100} placeholder="la-beaute"/></label>
              <label>Razão social<input name="legal_name" required maxLength={200}/></label>
              <label>Nome fantasia<input name="trade_name" required maxLength={200}/></label>
              <label>CNPJ / documento<input name="tax_id" maxLength={32}/></label>
              <label>E-mail da empresa<input name="email" type="email" required maxLength={255}/></label>
              <label>Telefone<input name="phone" maxLength={40}/></label>
            </div></div>
            <div className="platform-form-section"><div><span>PRIMEIRO ACESSO</span><h2>Acesso do proprietário</h2><p>Opcional. Para prospect ou possível cliente, deixe em branco. O contratante ficará Pendente de ativação e o OWNER poderá ser convidado posteriormente.</p></div><div className="platform-fields platform-fields-single">
              <label>E-mail de acesso do proprietário (opcional)<input name="owner_email" type="email" maxLength={255} placeholder="Preencher somente quando o acesso for liberado"/></label>
            </div></div>
            <div className="platform-form-actions"><Link href="/platform/clientes">Cancelar</Link><button type="submit">Cadastrar contratante</button></div>
          </form>
        </div>
      </section>
    </main>
  );
}
