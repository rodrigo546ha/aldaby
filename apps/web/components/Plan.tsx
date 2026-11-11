"use client";

import { useCallback, useEffect } from "react";

import type { components } from "../lib/api-types";
import { invalidatePlans, useApi } from "../lib/data";
import { formatValue, label } from "../lib/format";
import { Advisor } from "./Advisor";
import { Bids } from "./Bids";
import { TopicCharts, VerdictCascade } from "./Charts";
import { BrandHeader, useBranding } from "./Branding";
import { Changes, ExplainHead, Lede, notePoints, Points, pointsFrom, Steps } from "./Explain";
import { FigureBlock } from "./FigureView";
import { Skeleton, VerdictFigure } from "./Motion";
import { Icon } from "./Icon";
import { OfferPhoto } from "./OfferPhoto";
import { Questions } from "./Questions";
import { RentalAdvice } from "./RentalAdvice";
import { Renovation } from "./Renovation";
import { AppLink, DATA } from "./AppLink";

type PlanOut = components["schemas"]["PlanOut"];
type CatalogOut = components["schemas"]["CatalogOut"];

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
// Lo que pasa con tu cifra si las cosas van peor: dos escenarios que ya calcula el motor
const WORSE: { key: string; title: string }[] = [
  { key: "search.stressed_cashflow", title: "Con la subida de tipos" },
  { key: "plan.low_rent_cashflow", title: "Con la renta baja de la zona" },
];
const RENTAL: Record<string, string> = {
  habitual: "habitual",
  temporada: "de temporada",
  habitaciones: "por habitaciones",
  turistico: "turístico",
};

export function Plan({ offerId }: { offerId: string }) {
  const [brand, brandVersion] = useBranding();
  // El plan y la oferta, de la caché de la app: si se pidieron al pasar por el enlace, ya están
  const planApi = useApi<PlanOut>(`/api/plans/offers/${offerId}`, 120_000);
  // El título corto y la dirección de la oferta, los mismos que en la lista y en su ficha
  const offerApi = useApi<CatalogOut>(`/api/offers/catalog/${offerId}`);
  const plan = planApi.result?.ok ? planApi.result.data : null;
  const offer = offerApi.result?.ok ? offerApi.result.data : null;
  const failure =
    planApi.result && !planApi.result.ok
      ? planApi.result.status === 0
        ? "No se ha podido conectar con la API. ¿Está arrancada con make api?"
        : Array.isArray(planApi.result.detail)
          ? planApi.result.detail.join(". ")
          : typeof planApi.result.detail === "string"
            ? planApi.result.detail
            : "Error en el plan"
      : null;
  // Al guardar una renta esperada o una reforma cambian este plan, la búsqueda y la ficha: se
  // piden de nuevo
  const reload = useCallback(() => {
    invalidatePlans();
    void planApi.refresh();
  }, [planApi]);

  // Desde la ficha, «Simular mi puja» llega con #pujas: el plan se pinta después de la carga
  useEffect(() => {
    if (plan && window.location.hash)
      document.getElementById(window.location.hash.slice(1))?.scrollIntoView({ block: "start" });
  }, [plan]);

  if (failure) return <p className="failure">{failure}</p>;
  if (!plan) return <Skeleton label="Calculando tu plan…" />;

  const all = new Map(plan.sections.flatMap((s) => s.figures).map((f) => [f.key, f]));
  const blockOf = new Map(plan.sections.flatMap((s) => s.figures.map((f) => [f.key, s.id] as const)));
  const verdict = VERDICT.flatMap((v) => {
    const f = all.get(v.key);
    return f ? [{ ...v, figure: f }] : [];
  });
  const cash = all.get("cashflow.monthly_after_tax");
  const yearly = all.get("cashflow.annual_after_tax");
  const cascade = yearly && plan.breakdown.length > 1;
  const worse = cash
    ? WORSE.flatMap((w) => {
        const f = all.get(w.key);
        return f
          ? [{ key: w.key, label: w.title, before: formatValue(cash.value, cash.unit), after: formatValue(f.value, f.unit) }]
          : [];
      })
    : [];
  const sections = [...plan.sections].sort(
    (x, y) => (BLOCKS[x.id]?.order ?? 99) - (BLOCKS[y.id]?.order ?? 99),
  );
  const recommended = plan.advice?.types.find((t) => t.rental_type === plan.advice?.recommended);

  return (
    <div className="plan stagger">
      <BrandHeader brand={brand} version={brandVersion} />
      <AppLink className="back-link" href={`/oferta/${offerId}`} data={DATA.offer(offerId)} morph>
        <Icon name="back" small /> La oferta
      </AppLink>
      <OfferPhoto offerId={offerId} credit hideEmpty className="plan-photo" morph />
      <section className="verdict" aria-labelledby="verdict-title">
        <div className="verdict-head">
          <span className={plan.passes ? "status pass" : "status fail"}>
            {plan.passes ? "Encaja con tu plan" : "No encaja con tu plan"}
            {plan.auction ? " · subasta" : ""}
          </span>
          <h2 id="verdict-title">{offer?.title ?? plan.title ?? (plan.kind === "enlace" ? "Oferta pegada" : "Lote del BOE")}</h2>
          {offer && (offer.address || offer.place) && (
            <p className="verdict-address">{[offer.address, offer.place].filter(Boolean).join(" · ")}</p>
          )}
        </div>
        <div className={cascade ? "verdict-body with-cascade" : "verdict-body"}>
          <div className="verdict-side">
            <div className="verdict-figures">
              {verdict.map((v) => (
                <VerdictFigure key={v.key} figure={v.figure} title={v.title} />
              ))}
            </div>
            {worse.length > 0 && (
              <div className="verdict-worse">
                <ExplainHead>Tu cash flow si las cosas van peor</ExplainHead>
                <Changes rows={worse} />
              </div>
            )}
          </div>
          {cascade && <VerdictCascade breakdown={plan.breakdown} total={yearly} />}
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

      <Advisor offerId={offerId} blockOf={blockOf} />
      <Questions offerId={offerId} />

      {plan.arguments.length > 0 && (
        <section className="plan-section" aria-labelledby="motivos">
          <h3 id="motivos">Motivos para pensarlo</h3>
          <Points items={pointsFrom(plan.arguments.map((a) => a.text), "warning")} />
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
            <TopicCharts topic={s.id} figures={all} series={plan.series} />
            {s.id === "compra" && (
              <Renovation
                offerId={offerId}
                current={all.get("purchase_costs.renovation")?.value ?? null}
                onSaved={reload}
              />
            )}
            {s.id === "hipoteca" && plan.cheapest_mortgage && (
              <Points
                items={[
                  {
                    key: "hipoteca",
                    tone: "info",
                    title: "Fija o variable",
                    text: (
                      <>
                        Con la trayectoria esperada del Euríbor paga menos intereses{" "}
                        {MORTGAGE[plan.cheapest_mortgage] ?? plan.cheapest_mortgage}; con la subida de tipos, la cuota
                        más alta es menor en {MORTGAGE[plan.safest_mortgage ?? ""] ?? "—"}.
                      </>
                    ),
                  },
                ]}
              />
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
              <RentalAdvice offerId={offerId} advice={plan.advice} onSaved={reload} />
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
              <Lede>Hay normas pendientes de convalidación. Si se convalidan, estas cifras de tu plan cambian así:</Lede>
              <Changes
                rows={plan.pending_changes.map((c) => ({
                  key: c.key,
                  label: label(c.key),
                  before: formatValue(c.base.value, c.base.unit),
                  after: formatValue(c.scenario.value, c.scenario.unit),
                }))}
              />
            </div>
          </details>
        )}

        <details className="block" id="bloque-pasos">
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
            <Lede>Lo que hay que hacer, en orden. Los pasos aún no están verificados: antes de dar cada uno, lee su fuente.</Lede>
            {Object.keys(STAGES).map((stage) => {
              const steps = plan.roadmap.filter((s) => s.stage === stage);
              if (steps.length === 0) return null;
              return (
                <div key={stage} className="steps-stage">
                  <ExplainHead as="h4">{STAGES[stage]}</ExplainHead>
                  <Steps
                    items={steps.map((s) => ({ key: s.id, title: s.title, text: s.detail, href: s.source_url }))}
                  />
                </div>
              );
            })}
          </div>
        </details>

      </section>

      {plan.notes.length > 0 && (
        <details className="data-quality">
          <summary>Notas y calidad de los datos ({plan.notes.length})</summary>
          <Points items={notePoints(plan.notes)} />
        </details>
      )}
    </div>
  );
}
