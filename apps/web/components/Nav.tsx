"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { Account } from "./Access";
import { ClientPicker } from "./Clients";
import { Logo } from "./Logo";
import { ThemeToggle } from "./Theme";

// Barra de la aplicación (docs/PROPUESTA_UX.md, U6): cuatro destinos y, debajo, las secciones del
// destino en el que estás. Todas las direcciones de antes siguen valiendo. En la página de
// presentación no sale (ADR-0041). Un particular trabaja con su propio perfil: no ve Clientes ni
// Ajustes, que son del profesional.

type Section = { href: string; label: string };
type Destination = {
  href: string;
  label: string;
  professional: boolean;
  icon: ReactNode;
  sections: Section[];
  also?: string[]; // otras direcciones que pertenecen a este destino
};

const stroke = { fill: "none", stroke: "currentColor", strokeWidth: 1.6, strokeLinecap: "round", strokeLinejoin: "round" } as const;

const DESTINATIONS: Destination[] = [
  {
    href: "/mapa",
    label: "Ofertas",
    professional: false,
    icon: (
      <svg viewBox="0 0 24 24" aria-hidden="true" {...stroke}>
        <path d="M12 21s-6.5-5.4-6.5-11a6.5 6.5 0 0 1 13 0c0 5.6-6.5 11-6.5 11Z" />
        <circle cx="12" cy="10" r="2.4" />
      </svg>
    ),
    // Una sola lista de ofertas, en mapa o en lista (ADR-0054): sin secciones por canal
    sections: [{ href: "/mapa", label: "Ofertas" }],
    also: ["/plan/", "/ofertas", "/anuncios"],
  },
  {
    href: "/perfil",
    label: "Mi plan",
    professional: false,
    icon: (
      <svg viewBox="0 0 24 24" aria-hidden="true" {...stroke}>
        <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />
      </svg>
    ),
    sections: [
      { href: "/perfil", label: "Perfil" },
      { href: "/busqueda", label: "Supuestos" },
      { href: "/simulador", label: "Simulador" },
    ],
  },
  {
    href: "/clientes",
    label: "Clientes",
    professional: true,
    icon: (
      <svg viewBox="0 0 24 24" aria-hidden="true" {...stroke}>
        <circle cx="9" cy="8" r="3.5" />
        <path d="M2.5 20c.6-3.6 3.2-5.5 6.5-5.5s5.9 1.9 6.5 5.5M16 4.8a3.5 3.5 0 0 1 0 6.4M18.5 14.8c1.6.8 2.7 2.5 3 5.2" />
      </svg>
    ),
    sections: [],
  },
  {
    href: "/marca",
    label: "Ajustes",
    professional: true,
    icon: (
      <svg viewBox="0 0 24 24" aria-hidden="true" {...stroke}>
        <path d="M4 7h10M18 7h2M4 17h2M10 17h10" />
        <circle cx="16" cy="7" r="2.2" />
        <circle cx="8" cy="17" r="2.2" />
      </svg>
    ),
    sections: [
      { href: "/marca", label: "Tu marca" },
      { href: "/agencias", label: "Agencias" },
    ],
  },
];

const within = (path: string, href: string) => path === href || path.startsWith(`${href}/`);

function current(path: string): Destination | undefined {
  return DESTINATIONS.find(
    (d) => within(path, d.href) || d.sections.some((s) => within(path, s.href)) || d.also?.some((a) => path.startsWith(a)),
  );
}

export function AppNav() {
  const path = usePathname();
  const [particular, setParticular] = useState(false);
  const bar = useRef<HTMLElement>(null);

  useEffect(() => {
    if (path === "/" || path.startsWith("/acceso")) return;
    fetch("/api/auth/me")
      .then(async (resp) => (resp.ok ? setParticular((await resp.json()).role === "particular") : null))
      .catch(() => undefined);
  }, [path]);

  // El alto de la barra lo usan las páginas a pantalla completa (el mapa)
  useEffect(() => {
    const el = bar.current;
    if (!el) return;
    const set = () => document.documentElement.style.setProperty("--appbar-h", `${el.offsetHeight}px`);
    set();
    const ro = new ResizeObserver(set);
    ro.observe(el);
    return () => ro.disconnect();
  }, [path]);

  // En móvil las secciones se desplazan: la activa tiene que quedar a la vista
  useEffect(() => {
    document.querySelector('.subnav a[aria-current="page"]')?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }, [path]);

  if (path === "/") return null;
  // Sin sesión las secciones no sirven: en el acceso solo quedan la marca y el tema
  const outside = path.startsWith("/acceso");
  const shown = DESTINATIONS.filter((d) => !(particular && d.professional));
  const here = current(path);
  const sections = here && here.sections.length > 1 ? here.sections : [];
  return (
    <>
      <header ref={bar} className="appbar">
        <div className="appbar-inner">
          <Link href="/mapa" className="appbar-brand" aria-label="Aldaby, inicio de la aplicación">
            <Logo />
          </Link>
          {!outside && (
            <nav className="appnav" aria-label="Destinos">
              {shown.map((d) => (
                <Link key={d.href} href={d.href} aria-current={d === here ? "page" : undefined}>
                  {d.label}
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
        {!outside && sections.length > 0 && (
          <nav className="subnav" aria-label={`Secciones de ${here?.label ?? ""}`}>
            <div className="subnav-inner">
              {sections.map((s) => (
                <Link key={s.href} href={s.href} aria-current={within(path, s.href) ? "page" : undefined}>
                  {s.label}
                </Link>
              ))}
            </div>
          </nav>
        )}
      </header>
      {!outside && (
        // En móvil los destinos van abajo, al alcance del pulgar
        <nav className="tabbar" aria-label="Destinos">
          {shown.map((d) => (
            <Link key={d.href} href={d.href} aria-current={d === here ? "page" : undefined}>
              {d.icon}
              <span>{d.label}</span>
            </Link>
          ))}
        </nav>
      )}
    </>
  );
}
