"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { SplitText as GSAPSplitText } from "gsap/SplitText";
import { useRef, type RefObject } from "react";

gsap.registerPlugin(useGSAP, GSAPSplitText);

// Adaptado de SplitText de React Bits (reactbits.dev, MIT + Commons Clause) y reducido a lo que
// DESIGN.md admite (ADR-0069): el texto entra por líneas desde detrás de una máscara, una vez, al
// cargar. Sin rebote, sin bucle y sin efecto al pasar el puntero. El texto está en el HTML desde el
// servidor; GSAP lo parte en el navegador y deja al lector de pantalla la frase entera. Con
// movimiento reducido no se parte ni se mueve.
export function SplitText({
  text,
  tag = "h1",
  className,
}: {
  text: string;
  tag?: "h1" | "h2" | "p";
  className?: string;
}) {
  const ref = useRef<HTMLElement>(null);

  useGSAP(
    () => {
      const el = ref.current;
      if (!el) return;
      gsap.matchMedia().add("(prefers-reduced-motion: no-preference)", () => {
        // autoSplit vuelve a partir cuando llega la fuente o cambia el ancho; devolver la animación
        // en onSplit hace que siga donde iba
        const split = GSAPSplitText.create(el, {
          type: "lines",
          mask: "lines",
          autoSplit: true,
          onSplit: (self) =>
            gsap.from(self.lines, { yPercent: 105, duration: 0.9, ease: "power4.out", stagger: 0.09 }),
        });
        return () => split.revert();
      });
    },
    { scope: ref },
  );

  const Tag = tag as "h1";
  return (
    <Tag ref={ref as RefObject<HTMLHeadingElement>} className={className}>
      {text}
    </Tag>
  );
}
