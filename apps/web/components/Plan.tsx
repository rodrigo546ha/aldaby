"use client";

import { useEffect, useState } from "react";

import type { components } from "../lib/api-types";
import { formatValue, label } from "../lib/format";
import { Bids } from "./Bids";
import { BrandHeader, useBranding } from "./Branding";
import { FigureBlock, WarningItem } from "./FigureView";
import { Skeleton, VerdictFigure } from "./Motion";

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

// Orden de lectura: primero lo de cada mes y lo que pones, al final los supuestos. Cerrado, cada tema
// enseña sus cifras clave; las demás, con sus fórmulas, al abrirlo (docs/PROPUESTA_UX.md, U2).
const BLOCKS: Record<string, { order: number; keys: string[] }> = {
  explotacion: { order: 0, keys: ["cashflow.monthly_after_tax", "cashflow.gross_yield"] },
  compra: { order: 1, keys: ["purchase_costs.total", "cashflow.cash_invested"] },
  hipoteca: { order: 2, keys: ["mortgage.monthly_payment", "financing.years"] },
  estres: { order: 3, keys: ["term.stressed_monthly_cashflow"] },
  venta: { order: 4, keys: ["irr.rate", "irr.sale_price"] },
  capacidad: { order: 5, keys: ["affordability.max_price"] },
  supuestos: { order: 6, keys: [] },
};
const VERDICT: { key: string; title: string }[] = [
  { key: "cashflow.monthly_after_tax", title: "Tu cash flow tras impuestos" },
  { key: "cashflow.cash_invested", title: "Lo que pones" },
  { key: "irr.rate", title: "Rentabilidad anual (TIR)" },
];
const RENTAL: Record<string, string> = {
  habitual: "habitual",
  temporada: "de temporada",
  habitaciones: "por habitaciones",
  turistico: "turístico",
};

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
  if (!plan) return <Skeleton label="Calculando tu plan…" />;

  const all = new Map(plan.sections.flatMap((s) => s.figures).map((f) => [f.key, f]));
  const verdict = VERDICT.flatMap((v) => {
    const f = all.get(v.key);
    return f ? [{ ...v, figure: f }] : [];
  });
  const sections = [...plan.sections].sort(
    (x, y) => (BLOCKS[x.id]?.order ?? 99) - (BLOCKS[y.id]?.order ?? 99),
  );
  const recommended = plan.advice?.types.find((t) => t.rental_type === plan.advice?.recommended);

  return (
    <div className="plan stagger">
      <BrandHeader brand={brand} version={brandVersion} />
      <section className="verdict" aria-labelledby="verdict-title">
        <div className="verdict-head">
          <span className={plan.passes ? "status pass" : "status fail"}>
            {plan.passes ? "Encaja con tu plan" : "No encaja con tu plan"}
            {plan.auction ? " · subasta" : ""}
          </span>
          <h2 id="verdict-title">{plan.title ?? (plan.kind === "enlace" ? "Oferta pegada" : "Lote del BOE")}</h2>
        </div>
        <div className="verdict-figures">
          {verdict.map((v) => (
            <VerdictFigure key={v.key} figure={v.figure} title={v.title} />
          ))}
        </div>
        {plan.reasons.length > 0 && (
          <p className="verdict-reason">
            {plan.passes ? "Ojo: " : "No encaja porque "}
            {plan.reasons.map((r) => r.charAt(0).toLowerCase() + r.slice(1)).join(" y ")}.
          </p>
        )}
        <div className="verdict-actions">
          <a className="button-link" href={`/api/plans/offers/${offerId}/pdf`} download>
            Descargar PDF
          </a>
          {plan.url && (
            <a href={plan.url} target="_blank" rel="noreferrer">
              Ver la oferta
            </a>
          )}
        </div>
      </section>

      <Explanation offerId={offerId} />

      {plan.arguments.length > 0 && (
        <section className="plan-section" aria-labelledby="motivos">
          <h3 id="motivos">Motivos para pensarlo</h3>
          <ul className="arguments">
            {plan.arguments.map((a) => (
              <li key={a.code}>{a.text}</li>
            ))}
          </ul>
        </section>
      )}

      {/* La puja solo tiene sentido en una subasta */}
      {plan.auction && <Bids offerId={offerId} auction={plan.auction} />}

      <section className="plan-blocks" aria-label="Las cifras del plan">
        {sections.map((s) => (
          <FigureBlock
            key={s.id}
            id={s.id}
            title={s.title}
            figures={s.figures}
            keys={BLOCKS[s.id]?.keys ?? []}
          >
            {s.id === "hipoteca" && plan.cheapest_mortgage && (
              <p className="hint">
                Con la trayectoria esperada del Euríbor paga menos intereses{" "}
                {MORTGAGE[plan.cheapest_mortgage] ?? plan.cheapest_mortgage}; con la subida de tipos,
                la cuota más alta es menor en {MORTGAGE[plan.safest_mortgage ?? ""] ?? "—"}.
              </p>
            )}
          </FigureBlock>
        ))}

        {plan.advice && (
          <details className="block">
            <summary className="block-head">
              <span className="block-title">Cómo alquilarla</span>
              <span className="block-keys">
                <span className="block-key">
                  <span className="block-key-label">Recomendado</span>
                  <span className="block-key-value">
                    {plan.advice.recommended
                      ? `Alquiler ${RENTAL[plan.advice.recommended] ?? plan.advice.recommended}`
                      : "Sin recomendación"}
                  </span>
                </span>
                {recommended && (
                  <span className="block-key">
                    <span className="block-key-label">Gestión</span>
                    <span className="block-key-value">{recommended.management === "activa" ? "Activa" : "Pasiva"}</span>
                  </span>
                )}
              </span>
            </summary>
            <div className="block-body">
              <ul className="hint">
                {plan.advice.reasons.map((r) => (
                  <li key={r}>{r}</li>
                ))}
                {recommended && <li>{recommended.management_reason}</li>}
              </ul>
              <p className="hint">Los demás tipos, con sus requisitos, en la búsqueda.</p>
            </div>
          </details>
        )}

        {plan.pending_changes.length > 0 && (
          <details className="block">
            <summary className="block-head">
              <span className="block-title">Si se convalidan las normas pendientes</span>
              <span className="block-keys">
                <span className="block-key">
                  <span className="block-key-label">Cambios</span>
                  <span className="block-key-value">{plan.pending_changes.length}</span>
                </span>
              </span>
            </summary>
            <div className="block-body">
              <ul className="changes">
                {plan.pending_changes.map((c) => (
                  <li key={c.key}>
                    {label(c.key)}: {formatValue(c.base.value, c.base.unit)} →{" "}
                    {formatValue(c.scenario.value, c.scenario.unit)}
                  </li>
                ))}
              </ul>
            </div>
          </details>
        )}

        <details className="block">
          <summary className="block-head">
            <span className="block-title">Pasos para comprar</span>
            <span className="block-keys">
              <span className="block-key">
                <span className="block-key-label">Pasos</span>
                <span className="block-key-value">{plan.roadmap.length}</span>
              </span>
            </span>
          </summary>
          <div className="block-body">
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
          </div>
        </details>

      </section>

      {plan.notes.length > 0 && (
        <details className="data-quality">
          <summary>Notas y calidad de los datos ({plan.notes.length})</summary>
          <ul className="warnings">
            {plan.notes.map((n) => (
              <WarningItem key={n} text={n} />
            ))}
          </ul>
        </details>
      )}
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
      {busy && <Skeleton label="El asesor está leyendo tu plan" shape="text" />}
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
