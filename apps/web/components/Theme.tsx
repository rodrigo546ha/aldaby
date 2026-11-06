"use client";

import { useEffect, useState } from "react";

// Tema oscuro y claro. Sin elección guardada se sigue al sistema; el interruptor la guarda en este
// navegador. THEME_SCRIPT va en <head> para poner el tema antes de pintar y no dar un destello.

const KEY = "aldaby-tema";

export const THEME_SCRIPT =
  `try{var t=localStorage.getItem("${KEY}");if(t==="light"||t==="dark")` +
  `document.documentElement.dataset.theme=t}catch(e){}`;

type Theme = "light" | "dark";

function current(): Theme {
  const set = document.documentElement.dataset.theme;
  if (set === "light" || set === "dark") return set;
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme | null>(null);

  useEffect(() => setTheme(current()), []);

  function toggle() {
    const next: Theme = current() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem(KEY, next);
    } catch {
      // Sin almacenamiento el tema vale para esta visita
    }
    setTheme(next);
  }

  const toLight = theme !== "light";
  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={toggle}
      aria-label={toLight ? "Cambiar a tema claro" : "Cambiar a tema oscuro"}
      title={toLight ? "Tema claro" : "Tema oscuro"}
    >
      {/* Los dos iconos a la vez: el que se va encoge y se desenfoca mientras llega el otro (18) */}
      <span className="icon-swap">
        <svg viewBox="0 0 20 20" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.5"
             strokeLinecap="round" data-hidden={toLight ? undefined : ""}>
          <circle cx="10" cy="10" r="3.5" />
          <path d="M10 1.5v2M10 16.5v2M1.5 10h2M16.5 10h2M4 4l1.4 1.4M14.6 14.6 16 16M4 16l1.4-1.4M14.6 5.4 16 4" />
        </svg>
        <svg viewBox="0 0 20 20" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.5"
             strokeLinecap="round" data-hidden={toLight ? "" : undefined}>
          <path d="M16.5 12.2A7 7 0 0 1 7.8 3.5a7 7 0 1 0 8.7 8.7Z" />
        </svg>
      </span>
    </button>
  );
}
