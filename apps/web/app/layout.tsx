import type { Metadata } from "next";
import type { ReactNode } from "react";

import "@neondatabase/auth-ui/css";

import "./globals.css";
import "./product-polish.css";
import { BrowserSessionBoundary } from "./browser-session-boundary";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "HPTECH Beauty Coworking OS",
  description:
    "Gestão operacional de coworking de beleza, estética e bem-estar.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body><Providers><BrowserSessionBoundary />{children}</Providers></body>
    </html>
  );
}
