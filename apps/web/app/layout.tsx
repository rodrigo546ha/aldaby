import { Bricolage_Grotesque, Geist } from "next/font/google";
import type { ReactNode } from "react";

import { LegalFooter } from "../components/Legal";
import { AppNav } from "../components/Nav";
import { THEME_SCRIPT } from "../components/Theme";
import "./globals.css";

// Bricolage Grotesque es la letra del logotipo (docs/marca/): titulares y cifras grandes.
// Geist lleva la interfaz y los datos, con cifras tabulares. next/font las sirve desde la propia web.
const display = Bricolage_Grotesque({
  subsets: ["latin"],
  axes: ["opsz"],
  variable: "--font-display",
  display: "swap",
});
const text = Geist({ subsets: ["latin"], variable: "--font-text", display: "swap" });

export const metadata = {
  title: "Aldaby",
  description: "La inversión inmobiliaria con tus cifras: hipoteca, IRPF y gastos, con sus fuentes",
};

export const viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#0b2c23" },
    { media: "(prefers-color-scheme: light)", color: "#f6ebd0" },
  ],
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es" className={`${display.variable} ${text.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>
        <AppNav />
        {children}
        <LegalFooter />
      </body>
    </html>
  );
}
