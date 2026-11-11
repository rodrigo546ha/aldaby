"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useEffect, useRef, useState, type ReactNode } from "react";

import type { components } from "../lib/api-types";
import { formatValue, type FigureOut } from "../lib/format";
import { KnockerRing } from "./KnockerRing";
import { VerdictFigure } from "./Motion";
import { SplitText } from "./SplitText";

gsap.registerPlugin(useGSAP, ScrollTrigger);

type InvestmentRequest = components["schemas"]["InvestmentRequest"];
type InvestmentResponse = components["schemas"]["InvestmentResponse"];

// Portada (ADR-0069): alrededor de la anilla, tres cifras de un plan de ejemplo. Las calcula el
// motor con el mismo caso que «Rellenar con un ejemplo» del simulador; la web solo las enseña. Si
// la API no responde, la anilla se ve sin cifras.

const SHOWN: { key: string; title: (years: number) => string; you?: boolean }[] = [
  { key: "cashflow.monthly_after_tax", title: () => "Tu cash flow", you: true },
  { key: "mortgage.monthly_payment", title: () => "Cuota de la hipoteca" },
  { key: "irr.rate", title: (years) => `TIR a ${years} años` },
];

type Example = {
  figures: (FigureOut & { title: string; you?: boolean })[];
  price: string;
  rent: string;
  provisional: boolean;
};

async function loadExample(): Promise<Example | null> {
  // El caso de ejemplo vive con el simulador: se trae aparte para no cargarlo con la portada
  const { exampleRequest } = await import("./Simulator");
  const request: InvestmentRequest | null = exampleRequest();
  if (!request) return null;
  const resp = await fetch("/api/simulate/investment", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!resp.ok) return null;
  const body = (await resp.json()) as InvestmentResponse;
  const years = Number(request.exit?.horizon_years ?? 10);
  const figures = SHOWN.flatMap((s) => {
    const figure = body.figures[s.key];
    // el aviso de provisional va una vez, en el pie del ejemplo, no en cada cifra
    return figure ? [{ ...figure, provisional: false, title: s.title(years), you: s.you }] : [];
  });
  if (figures.length !== SHOWN.length) return null;
  return {
    figures,
    price: formatValue(String(request.property.price), "EUR"),
    rent: formatValue(String(request.rental.monthly_rent), "EUR/mes"),
    provisional: SHOWN.some((s) => body.figures[s.key]?.provisional),
  };
}

export function LandingHero({ children }: { children: ReactNode }) {
  const root = useRef<HTMLElement>(null);
  const shape = useRef({ flat: 0 });
  const [example, setExample] = useState<Example | null>(null);

  useEffect(() => {
    let alive = true;
    loadExample()
      .then((e) => alive && setExample(e))
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, []);

  // Al bajar, la anilla se cierra hasta verse de frente y las cifras se apagan. En móvil la anilla
  // es pequeña y sale de pantalla enseguida: ahí se queda como está.
  useGSAP(
    () => {
      gsap.matchMedia().add("(prefers-reduced-motion: no-preference) and (min-width: 921px)", () => {
        const figures = gsap.utils.toArray<HTMLElement>(".hero-figure");
        const closing = gsap
          .timeline({ scrollTrigger: { trigger: ".hero-ring", start: "center 48%", end: "center 0%", scrub: 0.6 } })
          .to(shape.current, { flat: 1, ease: "none" }, 0);
        if (figures.length) closing.to(figures, { autoAlpha: 0, stagger: 0.08, ease: "none" }, 0);
      });
    },
    { scope: root, dependencies: [example], revertOnUpdate: true },
  );

  return (
    <section className="hero" ref={root}>
      <div className="hero-copy">
        <SplitText text="Llama antes de comprar." />
        {children}
      </div>
      <div className="hero-ring">
        <KnockerRing shape={shape} />
        {example && (
          <>
            <div className="hero-figures">
              {example.figures.map((f, i) => (
                <div key={f.key} className={f.you ? "hero-figure you" : "hero-figure"} style={{ "--i": i } as React.CSSProperties}>
                  <VerdictFigure figure={f} title={f.title} />
                </div>
              ))}
            </div>
            <p className="hero-example">
              Plan de ejemplo{example.provisional && ", con cifras provisionales"}: un piso de {example.price}{" "}
              alquilado por {example.rent}. Lo calcula el motor ahora mismo, con las mismas reglas que el tuyo.
            </p>
          </>
        )}
      </div>
    </section>
  );
}

// «Cómo funciona» como recorrido: una línea avanza con el desplazamiento y cada paso se enciende
// cuando la línea llega. Sin movimiento, los tres pasos se ven como una lista.
export function StepsJourney({ children }: { children: ReactNode }) {
  const root = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      gsap.matchMedia().add("(prefers-reduced-motion: no-preference)", () => {
        gsap.fromTo(
          ".steps-line span",
          { scaleX: 0 },
          { scaleX: 1, ease: "none", scrollTrigger: { trigger: root.current, start: "top 78%", end: "top 28%", scrub: 0.4 } },
        );
        gsap.utils.toArray<HTMLElement>("li").forEach((step, i, all) => {
          ScrollTrigger.create({
            trigger: root.current,
            start: () => `top ${78 - ((i + 0.15) / all.length) * 50}%`,
            onEnter: () => step.classList.add("is-on"),
            onLeaveBack: () => step.classList.remove("is-on"),
          });
        });
        return () => root.current?.querySelectorAll("li.is-on").forEach((li) => li.classList.remove("is-on"));
      });
    },
    { scope: root },
  );

  return (
    <div className="steps-journey" ref={root}>
      <div className="steps-line" aria-hidden="true">
        <span />
      </div>
      {children}
    </div>
  );
}
