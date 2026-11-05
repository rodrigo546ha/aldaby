"use client";

import { useCallback, useEffect, useState } from "react";

// Caché de las respuestas de la API mientras la app está abierta: volver a una pantalla ya vista
// es instantáneo (se enseña lo guardado y se refresca por detrás) y dos componentes que piden lo
// mismo a la vez comparten una sola petición. Lo que cambia el plan (confirmar el perfil, guardar
// supuestos o una renta esperada, confirmar un anuncio) la vacía con `invalidate`. Al cambiar de
// cliente la página se recarga entera y la caché empieza de cero.

export type ApiResult<T> = { ok: true; data: T } | { ok: false; status: number; detail: unknown };

type Entry = { at: number; result?: ApiResult<unknown>; pending?: Promise<ApiResult<unknown>> };

const store = new Map<string, Entry>();
const listeners = new Map<string, Set<() => void>>();

function notify(url: string) {
  listeners.get(url)?.forEach((l) => l());
}

/** Lo que haya guardado para `url`, sin pedir nada. */
export function peek<T>(url: string): ApiResult<T> | undefined {
  return store.get(url)?.result as ApiResult<T> | undefined;
}

/**
 * La respuesta de `url`: la guardada si tiene menos de `maxAge` ms; si no, la pide (una sola
 * petición aunque la pidan varios a la vez). Un fallo de red cuenta como estado 0.
 */
export function load<T>(url: string, maxAge = 30_000, force = false): Promise<ApiResult<T>> {
  const entry = store.get(url);
  if (!force && entry?.result && Date.now() - entry.at < maxAge) return Promise.resolve(entry.result as ApiResult<T>);
  if (entry?.pending) return entry.pending as Promise<ApiResult<T>>;
  const pending = fetch(url)
    .then(async (resp): Promise<ApiResult<unknown>> => {
      const body = await resp.json().catch(() => ({}));
      return resp.ok ? { ok: true, data: body } : { ok: false, status: resp.status, detail: body?.detail };
    })
    .catch((): ApiResult<unknown> => ({ ok: false, status: 0, detail: null }))
    .then((result) => {
      // Un fallo no pisa una respuesta buena que ya hubiera: se sigue enseñando la anterior
      const keep = !result.ok && store.get(url)?.result?.ok;
      store.set(url, keep ? { ...store.get(url)!, pending: undefined } : { at: Date.now(), result });
      notify(url);
      return keep ? (store.get(url)!.result as ApiResult<unknown>) : result;
    });
  store.set(url, { ...(entry ?? { at: 0 }), pending });
  return pending as Promise<ApiResult<T>>;
}

/** Pide `url` por adelantado (al pasar por encima de un enlace, por ejemplo). */
export function prefetch(url: string, maxAge = 30_000): void {
  void load(url, maxAge);
}

/** Guarda una respuesta que ya se tiene (un elemento de una lista, por ejemplo). */
export function seed<T>(url: string, data: T): void {
  if (store.get(url)?.result) return;
  store.set(url, { at: 0, result: { ok: true, data } }); // at 0: se enseña, pero se refresca
}

/** Olvida todo lo que empiece por alguno de estos prefijos: lo próximo se pide de nuevo. */
export function invalidate(...prefixes: string[]): void {
  for (const url of [...store.keys()]) {
    if (prefixes.some((p) => url.startsWith(p))) {
      store.delete(url);
      notify(url);
    }
  }
}

/** Lo que cambia el plan del usuario: perfil, supuestos, rentas esperadas, anuncios confirmados. */
export function invalidatePlans(): void {
  invalidate("/api/search", "/api/plans", "/api/offers/catalog", "/api/profile");
}

/**
 * La respuesta de `url` para un componente: enseña al momento lo guardado y, si es más viejo que
 * `maxAge`, lo refresca por detrás. `url` null: todavía no hay nada que pedir.
 */
export function useApi<T>(url: string | null, maxAge = 30_000) {
  const [, repaint] = useState(0);
  useEffect(() => {
    if (!url) return;
    const listener = () => {
      if (!store.has(url)) void load(url, maxAge); // la vaciaron: se pide de nuevo para lo que está a la vista
      repaint((n) => n + 1);
    };
    const set = listeners.get(url) ?? new Set();
    set.add(listener);
    listeners.set(url, set);
    void load(url, maxAge);
    return () => {
      set.delete(listener);
    };
  }, [url, maxAge]);
  const refresh = useCallback(() => (url ? load<T>(url, 0, true) : Promise.resolve(undefined)), [url]);
  return { result: url ? peek<T>(url) : undefined, refresh };
}
