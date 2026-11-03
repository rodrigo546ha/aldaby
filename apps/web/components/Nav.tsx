"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { Account } from "./Access";
import { ClientPicker } from "./Clients";
import { Logo } from "./Logo";
import { ThemeToggle } from "./Theme";

// Barra de la aplicación. En la página de presentación no sale (ADR-0041). Un particular trabaja
// con su propio perfil: no ve Clientes, Agencias ni Marca, que son del profesional.

const LINKS = [
  { href: "/mapa", label: "Mapa", professional: false },
  { href: "/simulador", label: "Simulador", professional: false },
  { href: "/clientes", label: "Clientes", professional: true },
  { href: "/perfil", label: "Perfil", professional: false },
  { href: "/busqueda", label: "Búsqueda", professional: false },
  { href: "/ofertas", label: "Ofertas", professional: false },
  { href: "/anuncios", label: "Anuncios públicos", professional: false },
  { href: "/agencias", label: "Agencias", professional: true },
  { href: "/marca", label: "Marca", professional: true },
];

export function AppNav() {
  const path = usePathname();
  const [particular, setParticular] = useState(false);

  useEffect(() => {
    if (path === "/" || path.startsWith("/acceso")) return;
    fetch("/api/auth/me")
      .then(async (resp) => (resp.ok ? setParticular((await resp.json()).role === "particular") : null))
      .catch(() => undefined);
  }, [path]);

  // En móvil la barra se desplaza: la sección activa tiene que quedar a la vista
  useEffect(() => {
    document.querySelector('.appnav a[aria-current="page"]')?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }, [path, particular]);

  if (path === "/") return null;
  // Sin sesión las secciones no sirven: en el acceso solo quedan la marca y el tema
  const outside = path.startsWith("/acceso");
  return (
    <header className="appbar">
      <div className="appbar-inner">
        <Link href="/simulador" className="appbar-brand" aria-label="Aldaby, inicio de la aplicación">
          <Logo />
        </Link>
        {!outside && (
          <nav className="appnav" aria-label="Secciones">
            {LINKS.filter((l) => !(particular && l.professional)).map((l) => (
              <Link key={l.href} href={l.href} aria-current={path.startsWith(l.href) ? "page" : undefined}>
                {l.label}
              </Link>
            ))}
          </nav>
        )}
        <div className="appbar-tools">
          {!particular && !outside && <ClientPicker />}
          {!outside && <Account />}
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
