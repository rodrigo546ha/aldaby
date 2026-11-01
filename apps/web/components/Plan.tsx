"use client";

import { useEffect, useState } from "react";

import type { components } from "../lib/api-types";
import { formatValue, label } from "../lib/format";
import { BrandHeader, useBranding } from "./Branding";
import { FigureView } from "./FigureView";

type PlanOut = components["schemas"]["PlanOut"];
type ExplanationOut = components["schemas"]["ExplanationOut"];
type SegmentOut = components["schemas"]["SegmentOut"];

// Plan completo (F6.7, ADR-0025): las cifras las calcula la API; el asesor solo las explica
const STAGES: Record<string, string> = {
  antes: "Antes de comprometerte",
  compra: "La compra",
  despues: "Después de comprar",
};
const MORTGAGE: Record<string, string> = { fija: "la fija", variable: "la variable" };

export function Plan({ offerId }: { offerId: string }) {
  const [brand, brandVersion] = useBranding();
  const [plan, setPlan] = useState<PlanOut | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const resp = await fetch(`/api/plans/offers/${offerId}`);
        const body = await resp.json().catch(() => ({}));
        if (resp.ok) setPlan(body as PlanOut);
        else if (Array.isArray(body.detail)) setFailure(body.detail.join(". "));
        else setFailure(typeof body.detail === "string" ? body.detail : "Error en el plan");
      } catch {
        setFailure("No se ha podido conectar con la API. ¿Está arrancada con make api?");
      }
    })();
  }, [offerId]);

  if (failure) return <p className="failure">{failure}</p>;
  if (!plan) return <p className="empty">Calculando tu plan…</p>;
  return (
    <div className="plan">
      <BrandHeader brand={brand} version={brandVersion} />
      <section className="plan-head">
        <h2>{plan.title ?? (plan.kind === "enlace" ? "Oferta pegada" : "Lote del BOE")}</h2>
        <span className={plan.passes ? "status pass" : "status fail"}>
          {plan.passes ? "Encaja con tu plan" : "No encaja con tu plan"}
          {plan.auction ? " · subasta" : ""}
        </span>
        {plan.url && (
          <a href={plan.url} target="_blank" rel="noreferrer">
            Ver la oferta
          </a>
        )}
        <a href={`/api/plans/offers/${offerId}/pdf`} download>
          Descargar PDF
        </a>
        {plan.reasons.length > 0 && (
          <ul className="warnings">
            {plan.reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        )}
      </section>
      <Explanation offerId={offerId} />
      {plan.sections.map((s) => (
        <section key={s.id} className="plan-section" aria-labelledby={`section-${s.id}`}>
          <h3 id={`section-${s.id}`}>{s.title}</h3>
          {s.id === "hipoteca" && plan.cheapest_mortgage && (
            <p className="hint">
              Con la trayectoria esperada del Euríbor paga menos intereses{" "}
              {MORTGAGE[plan.cheapest_mortgage] ?? plan.cheapest_mortgage}; con la subida de tipos,
              la cuota más alta es menor en {MORTGAGE[plan.safest_mortgage ?? ""] ?? "—"}.
            </p>
          )}
          <div className="grid">
            {s.figures.map((f) => (
              <FigureView key={f.key} figure={f} />
            ))}
          </div>
        </section>
      ))}
      {plan.pending_changes.length > 0 && (
        <section className="plan-section">
          <h3>Si se convalidan las normas pendientes</h3>
          <ul className="changes">
            {plan.pending_changes.map((c) => (
              <li key={c.key}>
                {label(c.key)}: {formatValue(c.base.value, c.base.unit)} →{" "}
                {formatValue(c.scenario.value, c.scenario.unit)}
              </li>
            ))}
          </ul>
        </section>
      )}
      {plan.advice && (
        <section className="plan-section">
          <h3>Tipo de alquiler y gestión</h3>
          <p>
            {plan.advice.recommended
              ? `Recomendado: alquiler ${plan.advice.recommended}. `
              : "Sin recomendación. "}
            El detalle de cada tipo y sus requisitos, en la búsqueda.
          </p>
          <ul className="hint">
            {plan.advice.reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </section>
      )}
      <section className="plan-section">
        <h3>Argumentos para no comprar</h3>
        {plan.arguments.length === 0 ? (
          <p className="empty">Las cifras no dan ninguno.</p>
        ) : (
          <ul className="arguments">
            {plan.arguments.map((a) => (
              <li key={a.code}>
                {a.text}
                {a.figure_keys.length > 0 && (
                  <span className="origin"> · {a.figure_keys.map(label).join(", ")}</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
      <section className="plan-section">
        <h3>Hoja de ruta de compra</h3>
        <p className="hint">Pasos sin verificar todavía: lee la fuente de cada uno.</p>
        {Object.keys(STAGES).map((stage) => {
          const steps = plan.roadmap.filter((s) => s.stage === stage);
          if (steps.length === 0) return null;
          return (
            <div key={stage}>
              <h4>{STAGES[stage]}</h4>
              <ol className="roadmap">
                {steps.map((s) => (
                  <li key={s.id}>
                    <strong>{s.title}.</strong> {s.detail}{" "}
                    <a href={s.source_url} target="_blank" rel="noreferrer">
                      fuente
                    </a>
                  </li>
                ))}
              </ol>
            </div>
          );
        })}
      </section>
      <ul className="warnings">
        {plan.notes.map((n) => (
          <li key={n}>{n}</li>
        ))}
      </ul>
    </div>
  );
}

function Explanation({ offerId }: { offerId: string }) {
  const [result, setResult] = useState<ExplanationOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  async function ask() {
    setBusy(true);
    setFailure(null);
    try {
      const resp = await fetch(`/api/plans/offers/${offerId}/explanation`, { method: "POST" });
      const body = await resp.json().catch(() => ({}));
      if (resp.ok) setResult(body as ExplanationOut);
      else setFailure(typeof body.detail === "string" ? body.detail : "El asesor no ha respondido");
    } catch {
      setFailure("No se ha podido conectar con la API.");
    }
    setBusy(false);
  }

  return (
    <section className="plan-section explanation" aria-live="polite">
      <h3>Lo que dice el asesor</h3>
      {!result && (
        <button type="button" onClick={ask} disabled={busy}>
          {busy ? "El asesor está leyendo tu plan… (unos treinta segundos)" : "Explícame el plan"}
        </button>
      )}
      {failure && <p className="failure">{failure}</p>}
      {result && result.segments === null && (
        <p className="failure">
          El asesor no ha dado una explicación que se pueda comprobar ({result.failure}). Las
          cifras de abajo son las del plan.
        </p>
      )}
      {result?.segments && (
        <p className="agent-text">
          {result.segments.map((s, i) => (
            <SegmentView key={i} segment={s} />
          ))}
        </p>
      )}
      {result && result.extra_arguments.length > 0 && (
        <>
          <h4>Otros motivos para pensarlo, del asesor</h4>
          <p className="hint">No salen de las cifras del plan: son su opinión.</p>
          <ul className="arguments">
            {result.extra_arguments.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
        </>
      )}
    </section>
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
