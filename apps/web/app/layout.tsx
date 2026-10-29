import Link from "next/link";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata = {
  title: "HouseFinder",
  description: "La inversión inmobiliaria que encaja contigo",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es">
      <body>
        <nav className="topnav" aria-label="Secciones">
          <Link href="/">Simulador</Link>
          <Link href="/ofertas">Ofertas</Link>
          <Link href="/anuncios">Anuncios del BOE</Link>
        </nav>
        {children}
      </body>
    </html>
  );
}
