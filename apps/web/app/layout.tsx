import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";
import "./product-polish.css";

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
      <body>{children}</body>
    </html>
  );
}
