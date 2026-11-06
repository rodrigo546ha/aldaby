"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { ComponentProps, MouseEvent } from "react";

import { prefetch } from "../lib/data";

type Router = ReturnType<typeof useRouter>;
type WithTransitions = Document & { startViewTransition?: (update: () => Promise<void>) => unknown };

const MORPH_WAIT_MS = 400;

/**
 * Enlace dentro de la app: navega sin recargar la página (la barra, la caché y el mapa siguen
 * vivos) y, al pasar por encima o enfocarlo, pide por adelantado los datos de la pantalla a la que
 * lleva (`data`), para que al llegar ya estén.
 *
 * Con `morph`, la foto de la oferta pasa de esta pantalla a la siguiente (DESIGN.md, «Movimiento»,
 * regla 20) con la View Transitions API. Sin ella, o con movimiento reducido, se navega como siempre.
 */
export function AppLink({
  data = [],
  morph = false,
  onPointerEnter,
  onFocus,
  onClick,
  ...props
}: ComponentProps<typeof Link> & { data?: string[]; morph?: boolean }) {
  const router = useRouter();
  const warm = () => data.forEach((url) => prefetch(url));
  return (
    <Link
      {...props}
      onPointerEnter={(e) => {
        warm();
        onPointerEnter?.(e);
      }}
      onFocus={(e) => {
        warm();
        onFocus?.(e);
      }}
      onClick={(e) => {
        onClick?.(e);
        if (morph && typeof props.href === "string") transition(e, props.href, router);
      }}
    />
  );
}

function transition(e: MouseEvent, href: string, router: Router) {
  const doc = document as WithTransitions;
  if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  if (!doc.startViewTransition || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  e.preventDefault();
  doc.startViewTransition(() => arrive(href, router));
}

/**
 * Navega y espera a que la pantalla nueva esté puesta y con su foto cargada, para que la foto viaje
 * a su sitio. Si tarda, no se espera más de 400 ms: la página cambia igual, con un fundido.
 */
function arrive(href: string, router: Router): Promise<void> {
  const path = href.split(/[?#]/)[0];
  router.push(href);
  const start = performance.now();
  return new Promise((resolve) => {
    // Durante la transición el navegador no pinta, así que no hay requestAnimationFrame: temporizador
    const check = () => {
      const there = location.pathname === path;
      if ((there && document.querySelector("[data-morph][data-ready]")) || performance.now() - start > MORPH_WAIT_MS) {
        resolve();
      } else {
        setTimeout(check, 16);
      }
    };
    check();
  });
}

/** Los datos que pide cada pantalla, para pedirlos antes de llegar. */
export const DATA = {
  offer: (id: string) => [`/api/offers/catalog/${id}`, `/api/search/offers/${id}`],
  plan: (id: string) => [`/api/plans/offers/${id}`, `/api/offers/catalog/${id}`],
  map: () => ["/api/offers/catalog", "/api/search"],
};
