"use client";

import Link from "next/link";
import type { ComponentProps } from "react";

import { prefetch } from "../lib/data";

/**
 * Enlace dentro de la app: navega sin recargar la página (la barra, la caché y el mapa siguen
 * vivos) y, al pasar por encima o enfocarlo, pide por adelantado los datos de la pantalla a la que
 * lleva (`data`), para que al llegar ya estén.
 */
export function AppLink({
  data = [],
  onPointerEnter,
  onFocus,
  ...props
}: ComponentProps<typeof Link> & { data?: string[] }) {
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
    />
  );
}

/** Los datos que pide cada pantalla, para pedirlos antes de llegar. */
export const DATA = {
  offer: (id: string) => [`/api/offers/catalog/${id}`, `/api/search/offers/${id}`],
  plan: (id: string) => [`/api/plans/offers/${id}`, `/api/offers/catalog/${id}`],
  map: () => ["/api/offers/catalog", "/api/search"],
};
