"use client";

import { remaining, remainingDays, useNow, type Closing } from "../lib/closing";

/**
 * Lo que queda para el cierre de una oferta (DESIGN.md, «Datos clave»). Con la hora de la fuente,
 * un reloj que cambia cada segundo, sin animación; sin ella, solo los días. El lector de pantalla
 * oye lo que queda en palabras, no cada segundo.
 */
export function Countdown({ closing, date }: { closing: Closing; date: string }) {
  const now = useNow(closing.exact ? 1000 : 60_000);
  // Antes de saber la hora, un hueco del ancho del reloj: la fila no salta al montar
  if (now === null) return <span className="countdown" aria-hidden="true">&nbsp;</span>;
  if (closing.at <= now) return <span className="countdown">Cerrada</span>;
  if (!closing.exact) return <span className="countdown">{remainingDays(date, now)}</span>;
  const left = remaining(closing.at - now);
  return (
    <time className="countdown" dateTime={new Date(closing.at).toISOString()}>
      <span aria-hidden="true">{left.clock}</span>
      <span className="visually-hidden">{left.words}</span>
    </time>
  );
}
