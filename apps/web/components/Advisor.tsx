"use client";

import { useState } from "react";

import type { components } from "../lib/api-types";
import { formatValue, label } from "../lib/format";
import { Amount } from "./FigureView";
import { Lede, Points, pointsFrom } from "./Explain";
import { Skeleton } from "./Motion";

type ExplanationOut = components["schemas"]["ExplanationOut"];
type SegmentOut = components["schemas"]["SegmentOut"];

// El asesor en fichas (ADR-0052): mientras trabaja, la API cuenta lo que de verdad hace; el texto
// llega entero al final, ya comprobado. Ninguna cifra sale del modelo: cada una es un Figure.

const TOOLS: Record<string, string> = {
  plan_completo: "Repasa las cifras de tu plan",
  recomendar_alquiler: "Mira cómo alquilarla",
  valorar_oferta: "Valora la oferta",
  zona_de_oferta: "Mira la zona",
  buscar_ofertas: "La compara con tus otras ofertas",
  ofertas_guardadas: "Busca la oferta",
};

type Stage = { etapa: string; herramienta: string | null };

function stageLabel(stage: Stage, earlier: Stage[]): string {
  switch (stage.etapa) {
    case "modelo":
      return earlier.some((s) => s.etapa === "herramienta") ? "Escribe las fichas" : "Lee tu pregunta";
    case "herramienta":
      return TOOLS[stage.herramienta ?? ""] ?? "Consulta una herramienta";
    case "corrigiendo":
      return "Corrige algo que no se podía comprobar";
    case "argumentos":
      return "Busca otros motivos para pensarlo";
    default:
      return "Trabaja";
  }
}

/** Los bloques del SSE de la API: «event: nombre» y «data: json», separados por una línea vacía. */
async function* events(resp: Response): AsyncGenerator<{ name: string; data: unknown }> {
  const reader = resp.body!.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) return;
    buffer += value;
    let end;
    while ((end = buffer.indexOf("\n\n")) >= 0) {
      const block = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);
      const name = block.match(/^event: (.*)$/m)?.[1];
      const data = block.match(/^data: (.*)$/m)?.[1];
      if (name && data) yield { name, data: JSON.parse(data) };
    }
  }
}

/** Abre el tema del plan que tiene esa cifra y lo trae a la vista. */
function openBlock(id: string | undefined) {
  const el = id ? document.getElementById(`bloque-${id}`) : null;
  if (!(el instanceof HTMLDetailsElement)) return;
  el.open = true;
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  el.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" });
}

export function Advisor({ offerId, blockOf }: { offerId: string; blockOf: Map<string, string> }) {
  const [result, setResult] = useState<ExplanationOut | null>(null);
  const [stages, setStages] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  async function ask() {
    setBusy(true);
    setFailure(null);
    setStages([]);
    const seen: Stage[] = [];
    try {
      const resp = await fetch(`/api/plans/offers/${offerId}/explanation`, { method: "POST" });
      if (!resp.ok || !resp.body) {
        const body = await resp.json().catch(() => ({}));
        setFailure(typeof body.detail === "string" ? body.detail : "El asesor no ha respondido");
      } else {
        let done = false;
        for await (const event of events(resp)) {
          if (event.name === "etapa") {
            const stage = event.data as Stage;
            const text = stageLabel(stage, seen);
            seen.push(stage);
            setStages((all) => (all[all.length - 1] === text ? all : [...all, text]));
          } else if (event.name === "resultado") {
            setResult(event.data as ExplanationOut);
            done = true;
          } else if (event.name === "error") {
            setFailure((event.data as { detail?: string }).detail ?? "El asesor no ha podido terminar");
            done = true;
          }
        }
        if (!done) setFailure("El asesor no ha respondido");
      }
    } catch {
      setFailure("No se ha podido conectar con la API.");
    }
    setBusy(false);
  }

  return (
    <section className="plan-section explanation" aria-labelledby="asesor" aria-busy={busy}>
      <h3 id="asesor">Lo que dice el asesor</h3>
      {!result && !busy && (
        <div className="advisor-start">
          <button type="button" onClick={ask}>
            {failure ? "Volver a intentarlo" : "Explícame el plan"}
          </button>
          <span className="lede">Lo importante de tu plan en tres fichas, con las cifras de abajo.</span>
        </div>
      )}
      {busy && (
        <>
          <ol className="advisor-stages" aria-live="polite">
            {stages.map((s, i) => (
              <li key={`${i}-${s}`} className={i === stages.length - 1 ? "current" : "done"}>
                {s}
              </li>
            ))}
          </ol>
          <Skeleton label="El asesor está leyendo tu plan" shape="cards" />
        </>
      )}
      {failure && <p className="failure">{failure}</p>}
      {result && result.summary === null && (
        <p className="failure">El asesor no ha podido explicar este plan; las cifras de abajo son las del plan.</p>
      )}
      {result?.summary && (
        <div className="advisor" aria-live="polite">
          <p className="advisor-summary">
            <Segments parts={result.summary} />
          </p>
          <div className="advisor-cards">
            {result.cards.map((c, i) => (
              <article key={i} className="advisor-card" style={{ animationDelay: `${i * 70}ms` }}>
                <h4>{c.title}</h4>
                {c.figure && (
                  <button
                    type="button"
                    className="advisor-chip"
                    onClick={() => openBlock(blockOf.get(c.figure!.key))}
                    title={`${label(c.figure.key)}: ver en el plan`}
                  >
                    <Amount text={formatValue(c.figure.value, c.figure.unit)} />
                  </button>
                )}
                <p>
                  <Segments parts={c.text} />
                </p>
              </article>
            ))}
          </div>
          {result.risks.length > 0 && (
            <div className="advisor-risks">
              <h4>Riesgos</h4>
              <Points items={result.risks.map((r, i) => ({ key: String(i), tone: "warning", text: <Segments parts={r} /> }))} />
            </div>
          )}
          {result.next_step && (
            <div className="advisor-next">
              <span className="advisor-next-label">Siguiente paso</span>
              <p>
                <Segments parts={result.next_step} />
              </p>
              <button type="button" className="link-button" onClick={() => openBlock("pasos")}>
                Ver los pasos para comprar
              </button>
            </div>
          )}
        </div>
      )}
      {result && result.extra_arguments.length > 0 && (
        <details className="advisor-extra">
          <summary>Otros motivos para pensarlo, del asesor ({result.extra_arguments.length})</summary>
          <Lede>No salen de las cifras del plan: son su opinión.</Lede>
          <Points items={pointsFrom(result.extra_arguments, "warning")} />
        </details>
      )}
    </section>
  );
}

function Segments({ parts }: { parts: SegmentOut[] }) {
  return (
    <>
      {parts.map((s, i) => (
        <SegmentView key={i} segment={s} />
      ))}
    </>
  );
}

function SegmentView({ segment }: { segment: SegmentOut }) {
  if (segment.kind === "figure" && segment.figure) {
    const f = segment.figure;
    const text =
      segment.part === "low" && f.low !== null
        ? formatValue(f.low, f.unit)
        : segment.part === "high" && f.high !== null
          ? formatValue(f.high, f.unit)
          : segment.part === "range" && f.low !== null && f.high !== null
            ? `entre ${formatValue(f.low, f.unit)} y ${formatValue(f.high, f.unit)}`
            : formatValue(f.value, f.unit);
    return (
      <strong className="figure-ref" title={`${label(f.key)}: ${f.formula}`}>
        {text}
      </strong>
    );
  }
  if (segment.kind === "offer") return <em>{segment.label ?? "la oferta"}</em>;
  return <>{segment.text}</>;
}
