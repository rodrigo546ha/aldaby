"use client";

import { useEffect, useState } from "react";

import type { components } from "./api-types";

// Qué es cada fuente que cita una cifra (`GET /api/sources`): su nombre para leerlo, su cita legal
// o de dónde salen los valores, y su enlace oficial. Se piden juntas, una vez por página.

export type SourceInfo = components["schemas"]["SourceInfoOut"];
export type FigureSource = { kind: string; id: string; provisional: boolean };

/** La clave de una fuente: «rule:madrid-itp-inmuebles-2014»; sin tipo, solo el identificador. */
export const refKey = (s: { kind?: string; id: string }) => (s.kind ? `${s.kind}:${s.id}` : s.id);

const known = new Map<string, SourceInfo | null>(); // null: pedida y sin respuesta todavía
const pending = new Set<string>();
const listeners = new Set<() => void>();
let timer: ReturnType<typeof setTimeout> | null = null;
const CHUNK = 100;

function flush() {
  timer = null;
  const keys = [...pending];
  pending.clear();
  for (let i = 0; i < keys.length; i += CHUNK) {
    const query = keys
      .slice(i, i + CHUNK)
      .map((k) => `ref=${encodeURIComponent(k)}`)
      .join("&");
    fetch(`/api/sources?${query}`)
      .then((resp) => (resp.ok ? (resp.json() as Promise<SourceInfo[]>) : []))
      .then((list) => {
        for (const s of list) known.set(s.ref, s);
        listeners.forEach((l) => l());
      })
      .catch(() => undefined);
  }
}

/** Las fuentes ya conocidas de entre `keys`; las que faltan se piden y la vista se repinta. */
export function useSources(keys: string[]): Map<string, SourceInfo> {
  const [, repaint] = useState(0);
  const joined = keys.join("|");
  useEffect(() => {
    const listener = () => repaint((n) => n + 1);
    listeners.add(listener);
    for (const k of joined ? joined.split("|") : []) {
      if (known.has(k)) continue;
      known.set(k, null);
      pending.add(k);
    }
    if (pending.size > 0 && !timer) timer = setTimeout(flush, 0);
    return () => {
      listeners.delete(listener);
    };
  }, [joined]);
  const out = new Map<string, SourceInfo>();
  for (const k of keys) {
    const info = known.get(k);
    if (info) out.set(k, info);
  }
  return out;
}

/** Mientras llega su nombre: «gestoria-tasacion-y-copias» → «Gestoria tasacion y copias». */
export function humane(id: string): string {
  const text = id.split("@")[0].replace(/[-_]+/g, " ").trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

const HOSTS: [RegExp, string][] = [
  [/(^|\.)boe\.es$/, "BOE"],
  [/(^|\.)bocm\.es$/, "BOCM"],
  [/(^|\.)catastro\.(hacienda\.)?gob\.es$|catastro\.meh\.es$/, "Catastro"],
  [/(^|\.)hacienda\.gob\.es$/, "Hacienda"],
  [/(^|\.)ine\.es$/, "INE"],
  [/(^|\.)mivau\.gob\.es$/, "Ministerio de Vivienda"],
  [/(^|\.)bde\.es$/, "Banco de España"],
  [/(^|\.)ecb\.europa\.eu$/, "BCE"],
  [/(^|\.)comunidad\.madrid$/, "Comunidad de Madrid"],
];

/** De quién es el enlace oficial, para decirlo en el enlace: «BOE», «Catastro»… */
export function publisher(url: string): string {
  try {
    const host = new URL(url).hostname.replace(/^www\./, "");
    return HOSTS.find(([re]) => re.test(host))?.[1] ?? host;
  } catch {
    return "la fuente";
  }
}
