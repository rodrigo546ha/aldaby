"use client";

import "lenis/dist/lenis.css";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Lenis from "lenis";

gsap.registerPlugin(useGSAP, ScrollTrigger);

// Desplazamiento suave, solo en la portada (ADR-0069). Lenis comparte reloj con GSAP para que lo
// que va ligado al desplazamiento no vaya un fotograma por detrás. Con movimiento reducido no se
// crea: el desplazamiento es el del sistema.
export function SmoothScroll() {
  useGSAP(() => {
    gsap.matchMedia().add("(prefers-reduced-motion: no-preference)", () => {
      const lenis = new Lenis({ lerp: 0.1, anchors: true });
      lenis.on("scroll", ScrollTrigger.update);
      const tick = (time: number) => lenis.raf(time * 1000);
      gsap.ticker.add(tick);
      gsap.ticker.lagSmoothing(0);
      return () => {
        gsap.ticker.remove(tick);
        gsap.ticker.lagSmoothing(500, 33);
        lenis.destroy();
      };
    });
  });
  return null;
}
