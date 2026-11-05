"use client";

import { useState, type FormEvent } from "react";

import type { components } from "../lib/api-types";
import { amount } from "../lib/format";
import { ExplainHead, Lede, Points, pointsFrom, splitTitle } from "./Explain";
import { FigureView } from "./FigureView";

type RentalAdviceOut = components["schemas"]["RentalAdviceOut"];
type RentalTypeOut = components["schemas"]["RentalTypeOut"];

// Tipo de alquiler y gestión (F6.6, ADR-0024): la recomendación la hace la API
const RENTAL_LABEL: Record<string, string> = {
  habitual: "Habitual",
  temporada: "De temporada",
  habitaciones: "Por habitaciones",
  turistico: "Turístico",
};
const FIGURE_TITLE: Record<string, string> = {
  income: "Renta al mes",
  cashflow: "Cash flow al mes con su gestión",
  delegation_cost: "Lo que cuesta delegar al mes",
};
const REDUCTION: Record<string, string> = {
  true: "con reducción del IRPF",
  false: "sin reducción del IRPF",
  null: "reducción del IRPF por confirmar",
};

export function RentalAdvice({
  offerId,
  advice,
  onSaved,
}: {
  offerId: string;
  advice: RentalAdviceOut;
  onSaved: () => void;
}) {
  return (
    <section className="rental-advice" aria-label="Tipo de alquiler y gestión">
      <ExplainHead as="h4">
        {advice.recommended
          ? `Te recomendamos el alquiler ${RENTAL_LABEL[advice.recommended].toLowerCase()}`
          : "Cómo alquilarla"}
      </ExplainHead>
      <Points items={pointsFrom(advice.reasons, "info")} label="Por qué" />
      {advice.types.map((t) => (
        <RentalType
          key={t.rental_type}
          offerId={offerId}
          type={t}
          recommended={t.rental_type === advice.recommended}
          onSaved={onSaved}
        />
      ))}
      {advice.scenario.length > 0 && (
        <details className="explain-more">
          <summary>Si se convalidan las normas pendientes ({advice.scenario.length})</summary>
          <Points items={pointsFrom(advice.scenario, "warning")} />
        </details>
      )}
      <Points items={pointsFrom(advice.notes, "info")} label="Notas" />
    </section>
  );
}

function RentalType({
  offerId,
  type,
  recommended,
  onSaved,
}: {
  offerId: string;
  type: RentalTypeOut;
  recommended: boolean;
  onSaved: () => void;
}) {
  const income = type.figures.find((f) => f.key.endsWith(".income"));
  const [value, setValue] = useState(
    type.rental_type !== "habitual" && income ? income.value.replace(".", ",") : "",
  );
  const [error, setError] = useState<string | null>(null);

  async function save(event: FormEvent) {
    event.preventDefault();
    const parsed = value.trim() ? amount(value) : null;
    if (value.trim() && parsed === null) {
      setError("Escribe un importe, por ejemplo 1500 o 1500,50");
      return;
    }
    const resp = await fetch(`/api/search/offers/${offerId}/rent`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rental_type: type.rental_type, monthly_income: parsed }),
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      setError(typeof body.detail === "string" ? body.detail : "No se ha podido guardar");
      return;
    }
    setError(null);
    onSaved();
  }

  const summary = [
    RENTAL_LABEL[type.rental_type],
    type.allowed ? null : "no se puede ejercer",
    REDUCTION[String(type.irpf_reduction)],
    `gestión ${type.management}`,
  ].filter(Boolean);
  return (
    <details className={recommended ? "rental-type recommended" : "rental-type"} open={recommended}>
      <summary>
        {summary.join(" · ")}
        {recommended && <span className="status pass"> · recomendado</span>}
      </summary>
      <Lede>{type.management_reason}</Lede>
      <div className="grid">
        {type.figures.map((f) => (
          <FigureView key={f.key} figure={f} title={FIGURE_TITLE[f.key.split(".")[2]]} />
        ))}
      </div>
      <Points items={pointsFrom(type.notes, "warning")} label="Avisos" />
      {type.rental_type !== "habitual" && (
        <form className="rent-expectation" onSubmit={save}>
          <label htmlFor={`rent-${offerId}-${type.rental_type}`}>
            Lo que esperas sacar al mes de media (con los meses vacíos, sin limpieza, suministros
            ni comisiones)
          </label>
          <input
            id={`rent-${offerId}-${type.rental_type}`}
            inputMode="decimal"
            value={value}
            placeholder="€ al mes; vacío = sin cifras"
            onChange={(e) => setValue(e.target.value)}
          />
          <button type="submit">Guardar</button>
          {error && <p className="failure">{error}</p>}
        </form>
      )}
      {(type.regime || type.requirements.length > 0) && (
        <div className="rental-rules">
          <ExplainHead>Qué dice la ley</ExplainHead>
          {type.regime && <Lede>{type.regime}</Lede>}
          <Points
            items={type.requirements.map((r) => ({ key: r.code, ...splitTitle(r.description), href: r.source_url }))}
            label="Requisitos"
          />
        </div>
      )}
    </details>
  );
}
