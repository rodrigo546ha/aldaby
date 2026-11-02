import type { ReactNode } from "react";

import { VisitCounter } from "../components/Analytics";
import { LegalFooter } from "../components/Legal";
import { AppNav } from "../components/Nav";
import "./globals.css";

export const metadata = {
  title: "Aldaby",
  description: "La inversión inmobiliaria con tus cifras: hipoteca, IRPF y gastos, con sus fuentes",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es">
      <body>
        <AppNav />
        {children}
        <LegalFooter />
        <VisitCounter />
      </body>
    </html>
  );
}
