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
          <div className="platform-title"><span>ONBOARDING</span><h1>Cadastrar empresa contratante.</h1><p>Cria o tenant comercial e vincula o primeiro proprietário como convite de acesso.</p></div>
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
            <div className="platform-form-section"><div><span>PRIMEIRO ACESSO</span><h2>Proprietário responsável</h2><p>O cadastro nasce como Pendente de ativação. A credencial pertence à autoridade de identidade, não ao banco do BCOS.</p></div><div className="platform-fields platform-fields-single">
              <label>Identidade do proprietário<input name="owner_external_user_id" required maxLength={255} placeholder="Identidade confiável do OWNER"/></label>
            </div></div>
            <div className="platform-form-actions"><Link href="/platform/clientes">Cancelar</Link><button type="submit">Cadastrar contratante</button></div>
          </form>
        </div>
      </section>
    </main>
  );
}
