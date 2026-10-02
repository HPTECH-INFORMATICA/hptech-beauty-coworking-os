"""Transactional email delivery for BCOS."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from html import escape


@dataclass(frozen=True)
class EmailSettings:
    api_key: str
    email_from: str
    frontend_public_url: str

    @classmethod
    def from_env(cls) -> "EmailSettings":
        values = {
            name: os.getenv(name, "").strip()
            for name in ("RESEND_API_KEY", "EMAIL_FROM", "FRONTEND_PUBLIC_URL")
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise RuntimeError(f"Missing transactional email configuration: {', '.join(missing)}")
        return cls(
            api_key=values["RESEND_API_KEY"],
            email_from=values["EMAIL_FROM"],
            frontend_public_url=values["FRONTEND_PUBLIC_URL"].rstrip("/"),
        )


def send_professional_access_invitation(
    *,
    to_email: str,
    professional_name: str,
    tenant_name: str,
    settings: EmailSettings | None = None,
) -> None:
    config = settings or EmailSettings.from_env()
    access_url = f"{config.frontend_public_url}/auth/sign-in"
    safe_name = escape(professional_name)
    safe_tenant = escape(tenant_name)
    safe_url = escape(access_url, quote=True)
    payload = {
        "from": config.email_from,
        "to": [to_email],
        "subject": f"{tenant_name} convidou você para o Portal do Profissional",
        "html": (
            f"<h1>Olá, {safe_name}.</h1>"
            f"<p>A {safe_tenant} preparou seu acesso ao Portal do Profissional do BCOS.</p>"
            "<p>Entre ou crie sua conta usando este mesmo e-mail. "
            "Depois da autenticação, o BCOS apresentará o vínculo para sua confirmação.</p>"
            f'<p><a href="{safe_url}">Acessar convite profissional</a></p>'
            "<p>Este convite é pessoal e expira em 7 dias.</p>"
        ),
    }
    request = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "BCOS/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status < 200 or response.status >= 300:
                raise RuntimeError("Transactional email provider rejected the invitation.")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError("Professional invitation email could not be delivered.") from exc
