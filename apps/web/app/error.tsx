"use client";

import Link from "next/link";
import { useEffect } from "react";

export default function ErrorPage({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => { console.error("BCOS route error", error); }, [error]);

  return (
    <main className="product-error-page">
      <section>
        <span>BCOS</span>
        <h1>Não foi possível concluir esta tela</h1>
        <p>Seu acesso continua protegido. Tente carregar a tela novamente; se o problema persistir, retorne à visão geral.</p>
        <div>
          <button type="button" onClick={() => reset()}>Tentar novamente</button>
          <Link href="/">Ir para visão geral</Link>
        </div>
        {error.digest ? <small>Referência: {error.digest}</small> : null}
      </section>
    </main>
  );
}
