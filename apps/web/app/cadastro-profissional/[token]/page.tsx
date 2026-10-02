import { getPublicProfessionalOnboarding } from "../../lib/bcos-api";
import { submitProfessionalRegistration } from "./actions";

export const dynamic = "force-dynamic";

export default async function ProfessionalRegistrationPage({ params, searchParams }: { params: Promise<{ token: string }>; searchParams: Promise<{ enviado?: string }> }) {
  const { token } = await params;
  const query = await searchParams;
  const onboarding = await getPublicProfessionalOnboarding(token);
  if (query.enviado === "1") {
    return <main className="public-onboarding-shell"><section className="public-onboarding-card"><span>CADASTRO RECEBIDO</span><h1>Agora é com a {onboarding.tenant_name}.</h1><p>Seus dados e aceites foram registrados. A unidade analisará seu vínculo. Quando aprovado, você receberá no e-mail informado as instruções para criar ou acessar sua conta no Portal do Profissional.</p></section></main>;
  }
  const action = submitProfessionalRegistration.bind(null, token);
  return <main className="public-onboarding-shell"><section className="public-onboarding-card"><span>PORTAL DO PROFISSIONAL · {onboarding.tenant_name}</span><h1>Solicite seu acesso profissional.</h1><p>Preencha seus próprios dados. Seu acesso só será liberado após análise da unidade e confirmação da sua conta.</p><form action={action} className="public-onboarding-form"><label>Nome completo<input name="name" required autoComplete="name"/></label><label>E-mail<input name="email" type="email" required autoComplete="email"/></label><label>Celular<input name="phone" autoComplete="tel"/></label><label>Profissão<input name="profession"/></label><div className="public-onboarding-grid"><label>Conselho profissional<input name="council_type" placeholder="Ex.: COREN, CRM"/></label><label>Número do conselho<input name="council_number"/></label></div><div className="public-onboarding-documents">{onboarding.documents.map((document) => <article key={document.id}><div><strong>{document.title}</strong><span>Versão {document.version}</span></div><div className="public-onboarding-document-content">{document.content}</div><label className="public-onboarding-accept"><input type="checkbox" name="accepted_document_ids" value={document.id} required/>Li e aceito este documento.</label></article>)}</div><button type="submit">Enviar cadastro para análise</button></form></section></main>;
}
