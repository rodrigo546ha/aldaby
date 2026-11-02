"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { Account } from "./Access";
import { ClientPicker } from "./Clients";

// Barra de la aplicación. En la página de presentación no sale (ADR-0040). Un particular trabaja
// con su propio perfil: no ve Clientes, Agencias ni Marca, que son del profesional.

const LINKS = [
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

  if (path === "/") return null;
  return (
    <nav className="topnav" aria-label="Secciones">
      <Link href="/simulador" className="topnav-brand" aria-label="Aldaby, inicio de la aplicación">
        <picture>
          <source srcSet="/marca/aldaby-simbolo-negativo.svg" media="(prefers-color-scheme: dark)" />
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/marca/aldaby-simbolo.svg" alt="" width={22} height={22} />
        </picture>
      </Link>
      {LINKS.filter((l) => !(particular && l.professional)).map((l) => (
        <Link key={l.href} href={l.href} aria-current={path.startsWith(l.href) ? "page" : undefined}>
          {l.label}
        </Link>
      ))}
      {!particular && <ClientPicker />}
      <Account />
    </nav>
  );
}
