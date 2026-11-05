import type { CSSProperties } from "react";

import type { components } from "./api-types";
import { formatShortDate } from "./format";

// Lo que comparten la lista de ofertas y la ficha de una oferta (ADR-0054, DESIGN.md)

export type CatalogOut = components["schemas"]["CatalogOut"];
export type Channel = CatalogOut["channel"];
export type Group = "todas" | "subastas" | "directas" | "agencias" | "tuyos";

export const CHANNEL: Record<Channel, { label: string; group: Group }> = {
  subasta_judicial: { label: "Subasta judicial", group: "subastas" },
  subasta_administrativa: { label: "Subasta administrativa", group: "subastas" },
  subasta_notarial: { label: "Subasta notarial", group: "subastas" },
  venta_directa: { label: "Venta directa", group: "directas" },
  agencia: { label: "Agencia", group: "agencias" },
  tu_anuncio: { label: "Tu anuncio", group: "tuyos" },
};

export const TYPE_LABEL: Record<string, string> = {
  vivienda: "Vivienda",
  local: "Local",
  oficina: "Oficina",
  garaje: "Garaje",
  trastero: "Trastero",
  edificio: "Edificio",
  suelo: "Suelo",
  rustica: "Finca rústica",
  otro: "Otro inmueble",
};

/** El color del canal para un elemento: lo leen `--ch` en la etiqueta, el filo y el punto. */
export const channelStyle = (c: Channel) => ({ "--ch": `var(--ch-${c.replace("_", "-")})` }) as CSSProperties;

export const priceLabel = (o: CatalogOut) => (o.price_kind === "valor_subasta" ? "Valor de subasta" : "Precio");

/** Cuándo acaba: la subasta del Portal o el plazo de la venta directa. */
export function ending(o: CatalogOut): string | null {
  if (!o.ends_on) return o.auction_state === "Próxima apertura" ? "Abre pronto" : null;
  return `${o.channel === "venta_directa" ? "Hasta el" : "Termina el"} ${formatShortDate(o.ends_on)}`;
}

const area = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 0 });
export const formatArea = (m2: string) => `${area.format(Number(m2))} m²`;
