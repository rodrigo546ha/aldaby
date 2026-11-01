import Link from "next/link";
import type { ReactNode } from "react";

import { Account } from "../components/Access";
import { ClientPicker } from "../components/Clients";
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
          <Link href="/clientes">Clientes</Link>
          <Link href="/perfil">Perfil</Link>
          <Link href="/busqueda">Búsqueda</Link>
          <Link href="/ofertas">Ofertas</Link>
          <Link href="/anuncios">Anuncios del BOE</Link>
          <ClientPicker />
          <Account />
        </nav>
        {children}
      </body>
    </html>
  );
}
