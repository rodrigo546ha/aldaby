import { useEffect, useState } from "react";

import type { components } from "./api-types";

// Cuánto falta para que cierre una oferta. La fecha y la hora son las que da la fuente, en hora
// peninsular; aquí solo se restan del reloj. Sin fecha, o con la subasta sin abrir, no hay cuenta.

type Offer = Pick<
  components["schemas"]["CatalogOut"],
  "ends_on" | "ends_time" | "auction" | "auction_state" | "channel"
>;

/** Una oferta «cierra pronto» si le quedan menos de tres días: lo dicen el punto, la tarjeta y el panel. */
export const SOON_MS = 72 * 3_600_000;
const DAY_MS = 86_400_000;

const MADRID = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Europe/Madrid",
  hourCycle: "h23",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
});

/** Lo que marca el reloj de la península en ese instante, como si fuera UTC. */
function madridClock(instant: number): number {
  const p = Object.fromEntries(MADRID.formatToParts(new Date(instant)).map((x) => [x.type, Number(x.value)]));
  return Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute, p.second);
}

/** El instante en que en la península son las `time` del día `date`, esté donde esté el navegador. */
function madridInstant(date: string, time: string): number {
  const [y, m, d] = date.split("-").map(Number);
  const [hh, mm] = time.split(":").map(Number);
  const wall = Date.UTC(y, m - 1, d, hh, mm);
  return wall - (madridClock(wall) - wall);
}

export type Closing = {
  /** El instante del cierre. Sin hora en la fuente, el final de ese día. */
  at: number;
  /** La fuente da la hora: se puede contar hasta el segundo. */
  exact: boolean;
};

export function closing(o: Offer): Closing | null {
  if (!o.ends_on) return null;
  // Una subasta que no se está celebrando (sin abrir, suspendida) no tiene reloj
  if (o.auction && o.auction_state && o.auction_state !== "Celebrándose") return null;
  return o.ends_time
    ? { at: madridInstant(o.ends_on, o.ends_time), exact: true }
    : { at: madridInstant(o.ends_on, "23:59") + 59_999, exact: false };
}

export function closesSoon(o: Offer, now: number | null): boolean {
  const c = now === null ? null : closing(o);
  return c !== null && now !== null && c.at > now && c.at - now <= SOON_MS;
}

/** Días de calendario, en la península, de hoy al día del cierre. */
function daysUntil(date: string, now: number): number {
  const [y, m, d] = date.split("-").map(Number);
  const today = madridClock(now);
  return Math.round((Date.UTC(y, m - 1, d) - (today - (today % DAY_MS))) / DAY_MS);
}

/** «Cierra hoy a las 18:00», «Cierra mañana», «Cierra en 2 días»; nada si aún no cierra pronto. */
export function closingLabel(o: Offer, now: number | null): string | null {
  if (!closesSoon(o, now) || !o.ends_on || now === null) return null;
  const verb = o.channel === "venta_directa" ? "El plazo acaba" : "Cierra";
  const days = daysUntil(o.ends_on, now);
  const hour = o.ends_time ? ` a las ${o.ends_time}` : "";
  if (days <= 0) return `${verb} hoy${hour}`;
  if (days === 1) return `${verb} mañana${hour}`;
  return `${verb} en ${days} días`;
}

const two = (n: number) => String(n).padStart(2, "0");

/** Lo que queda, en dos formas: la del reloj («2 d 04:12:55») y la que se lee («2 días y 4 horas»). */
export function remaining(ms: number): { clock: string; words: string } {
  const s = Math.max(0, Math.floor(ms / 1000));
  const days = Math.floor(s / 86_400);
  const hours = Math.floor((s % 86_400) / 3600);
  const minutes = Math.floor((s % 3600) / 60);
  const clock = `${days > 0 ? `${days} d ` : ""}${two(hours)}:${two(minutes)}:${two(s % 60)}`;
  const unit = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;
  const words =
    days > 0
      ? `${unit(days, "día", "días")} y ${unit(hours, "hora", "horas")}`
      : hours > 0
        ? `${unit(hours, "hora", "horas")} y ${unit(minutes, "minuto", "minutos")}`
        : unit(minutes, "minuto", "minutos");
  return { clock, words };
}

/** Días enteros que quedan, para una fecha sin hora: «hoy», «mañana», «3 días». */
export function remainingDays(date: string, now: number): string {
  const days = daysUntil(date, now);
  return days <= 0 ? "hoy" : days === 1 ? "mañana" : `${days} días`;
}

/**
 * La hora de ahora, que avanza cada `stepMs`. Antes de montar es `null`: el servidor y el primer
 * pintado no saben qué hora es, y así no discrepan.
 */
export function useNow(stepMs: number): number | null {
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    setNow(Date.now());
    const timer = setInterval(() => setNow(Date.now()), stepMs);
    return () => clearInterval(timer);
  }, [stepMs]);
  return now;
}
