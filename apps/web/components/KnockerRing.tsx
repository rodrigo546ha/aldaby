"use client";

import { useEffect, useRef, type RefObject } from "react";

// La anilla de la aldaba (docs/marca/) como un toro de puntos que gira despacio en la portada.
// Decorativa: con movimiento reducido se queda quieta, y fuera de pantalla no se dibuja. `shape.flat`
// va de 0 (el toro inclinado) a 1 (el aro visto de frente): la portada lo liga al desplazamiento.

const RING = 220; // puntos a lo largo de la anilla
const TUBE = 14; // puntos alrededor del grosor
const R = 1; // radio de la anilla
const r = 0.3; // radio del tubo
const THIN = 0.03; // radio del tubo cuando la anilla se cierra

type Dot = { cu: number; su: number; cv: number; sv: number; tone: number };

function torus(): Dot[] {
  const dots: Dot[] = [];
  for (let i = 0; i < RING; i++) {
    const u = (i / RING) * Math.PI * 2;
    for (let j = 0; j < TUBE; j++) {
      // Desfase por vuelta: los puntos no forman filas rectas y la anilla se lee como materia
      const v = ((j + (i % 2) * 0.5) / TUBE) * Math.PI * 2;
      dots.push({ cu: Math.cos(u), su: Math.sin(u), cv: Math.cos(v), sv: Math.sin(v), tone: (Math.sin(u * 2 + 0.6) + 1) / 2 });
    }
  }
  return dots;
}

export function KnockerRing({ shape }: { shape?: RefObject<{ flat: number }> }) {
  const canvas = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const el = canvas.current;
    const ctx = el?.getContext("2d");
    if (!el || !ctx) return;
    const dots = torus();
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let frame = 0;
    let visible = true;
    let size = 0;
    let last = 0;

    function resize() {
      if (!el || !ctx) return;
      const box = el.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      size = box.width;
      el.width = box.width * dpr;
      el.height = box.height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      draw(last); // cambiar el tamaño del lienzo lo borra
    }

    function draw(t: number) {
      if (!ctx) return;
      last = t;
      const style = getComputedStyle(document.documentElement);
      const near = style.getPropertyValue("--ring-near").trim() || "#f2c66b";
      const far = style.getPropertyValue("--ring-far").trim() || "#9fd9bf";
      ctx.clearRect(0, 0, size, size);
      const flat = shape?.current?.flat ?? 0;
      const tube = r + (THIN - r) * flat;
      const a = (1.05 + Math.sin(t / 9000) * 0.12) * (1 - flat); // inclinación hacia el que mira
      const b = t / 7000; // giro sobre su eje
      const ca = Math.cos(a), sa = Math.sin(a), cb = Math.cos(b), sb = Math.sin(b);
      const scale = size * 0.33;
      const cx = size / 2, cy = size / 2;
      for (const d of dots) {
        const ring = R + tube * d.cv;
        const x0 = ring * d.cu, y0 = ring * d.su, z0 = tube * d.sv;
        const x1 = x0 * cb - y0 * sb;
        const y1 = x0 * sb + y0 * cb;
        const y2 = y1 * ca - z0 * sa;
        const z2 = y1 * sa + z0 * ca;
        const depth = (z2 + R + r) / (2 * (R + r)); // 0 lejos, 1 cerca
        const p = 2.6 / (2.6 - z2);
        ctx.globalAlpha = 0.18 + depth * 0.72;
        ctx.fillStyle = d.tone * depth > 0.32 ? near : far;
        const radius = (0.6 + depth * 1.3) * (size / 520);
        ctx.beginPath();
        ctx.arc(cx + x1 * scale * p, cy + y2 * scale * p, radius, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
    }

    function loop(t: number) {
      if (visible) draw(t);
      frame = requestAnimationFrame(loop);
    }

    resize();
    const observer = new IntersectionObserver(([entry]) => (visible = entry.isIntersecting));
    observer.observe(el);
    window.addEventListener("resize", resize);
    // Los colores salen del tema: con la anilla quieta hay que volver a dibujarla al cambiarlo
    const redraw = () => draw(last);
    const themes = new MutationObserver(redraw);
    themes.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    const scheme = window.matchMedia("(prefers-color-scheme: light)");
    scheme.addEventListener("change", redraw);
    if (!still) frame = requestAnimationFrame(loop);
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      themes.disconnect();
      scheme.removeEventListener("change", redraw);
      window.removeEventListener("resize", resize);
    };
  }, [shape]);

  return <canvas ref={canvas} className="knocker-ring" aria-hidden="true" />;
}
