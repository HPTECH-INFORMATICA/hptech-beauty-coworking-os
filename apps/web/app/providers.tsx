"use client";

import { NeonAuthUIProvider } from "@neondatabase/auth-ui";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";

import { authClient } from "../lib/auth/client";

const ptBRAuthLocalization = {
  SIGN_IN: "Entrar",
  SIGN_IN_ACTION: "Entrar",
  SIGN_IN_DESCRIPTION: "Informe seu e-mail e senha para acessar sua conta",
  SIGN_UP: "Criar conta",
  SIGN_UP_ACTION: "Criar conta",
  SIGN_UP_DESCRIPTION: "Informe seus dados para criar sua conta",
  ALREADY_HAVE_AN_ACCOUNT: "Já possui uma conta?",
  DONT_HAVE_AN_ACCOUNT: "Ainda não possui uma conta?",
  EMAIL: "E-mail",
  EMAIL_PLACEHOLDER: "seu@email.com",
  EMAIL_REQUIRED: "O e-mail é obrigatório",
  EMAIL_INSTRUCTIONS: "Informe um endereço de e-mail válido.",
  PASSWORD: "Senha",
  PASSWORD_PLACEHOLDER: "Senha",
  PASSWORD_REQUIRED: "A senha é obrigatória",
  FORGOT_PASSWORD: "Esqueci minha senha",
  FORGOT_PASSWORD_LINK: "Esqueceu sua senha?",
  FORGOT_PASSWORD_ACTION: "Enviar link de redefinição",
  FORGOT_PASSWORD_DESCRIPTION: "Informe seu e-mail para redefinir sua senha",
  FORGOT_PASSWORD_EMAIL: "Verifique seu e-mail para acessar o link de redefinição de senha.",
  RESET_PASSWORD: "Redefinir senha",
  RESET_PASSWORD_ACTION: "Salvar nova senha",
  RESET_PASSWORD_DESCRIPTION: "Informe sua nova senha",
  RESET_PASSWORD_SUCCESS: "Senha redefinida com sucesso",
  NEW_PASSWORD: "Nova senha",
  NEW_PASSWORD_PLACEHOLDER: "Nova senha",
  NEW_PASSWORD_REQUIRED: "A nova senha é obrigatória",
  CONFIRM_PASSWORD: "Confirmar senha",
  CONFIRM_PASSWORD_PLACEHOLDER: "Confirmar senha",
  CONFIRM_PASSWORD_REQUIRED: "A confirmação da senha é obrigatória",
  PASSWORDS_DO_NOT_MATCH: "As senhas não coincidem",
  SIGN_OUT: "Sair",
  CONTINUE: "Continuar",
  CANCEL: "Cancelar",
  GO_BACK: "Voltar",
  REQUEST_FAILED: "Não foi possível concluir a solicitação",
  UNEXPECTED_ERROR: "Ocorreu um erro inesperado",
  INVALID_EMAIL_OR_PASSWORD: "E-mail ou senha inválidos",
  INVALID_USERNAME_OR_PASSWORD: "Usuário ou senha inválidos",
  USER_NOT_FOUND: "Usuário não encontrado",
  INVALID_PASSWORD: "Senha inválida",
  PASSWORD_TOO_SHORT: "A senha é muito curta",
  PASSWORD_TOO_LONG: "A senha é muito longa",
  SESSION_EXPIRED: "Sua sessão expirou. Entre novamente.",
  VERIFY_YOUR_EMAIL: "Verifique seu e-mail",
  VERIFY_YOUR_EMAIL_DESCRIPTION:
    "Verifique seu endereço de e-mail. Consulte sua caixa de entrada para continuar.",
  EMAIL_VERIFICATION: "Verificação de e-mail",
  EMAIL_VERIFICATION_SUCCESS: "E-mail verificado com sucesso.",
  RESEND_VERIFICATION_EMAIL: "Reenviar e-mail de verificação",
} as const;

export function Providers({ children }: { children: ReactNode }) {
  const router = useRouter();

  return (
    <NeonAuthUIProvider
      authClient={authClient}
      navigate={router.push}
      replace={router.replace}
      onSessionChange={() => router.refresh()}
      localization={ptBRAuthLocalization}
    >
      {children}
    </NeonAuthUIProvider>
  );
}
