"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";

import type { components } from "../lib/api-types";
import { amount, formatValue, label, percentToRatio } from "../lib/format";
import { TopicCharts } from "./Charts";
import { Changes, ExplainHead, Lede, notePoints, Points, SourceList } from "./Explain";
import { FigureBlock } from "./FigureView";
import { Callout } from "./Icon";
import { Skeleton, Swap, VerdictFigure } from "./Motion";
import { MunicipalityPicker } from "./MunicipalityPicker";

type InvestmentRequest = components["schemas"]["InvestmentRequest"];
type InvestmentResponse = components["schemas"]["InvestmentResponse"];
type Region = components["schemas"]["RegionOut"];

type Kind = "eur" | "pct" | "int" | "text" | "date" | "bool" | "contract" | "deed" | "region" | "municipality";
type Field = { id: string; label: string; kind: Kind; hint?: string; optional?: boolean };
type Section = { title: string; description: string; fields: Field[] };

const SECTIONS: Section[] = [
  {
    title: "Tú",
    description: "Para saber cuánto te prestan y cuánto pagas de IRPF.",
    fields: [
      { id: "net_monthly_income", label: "Ingresos netos al mes", kind: "eur" },
      { id: "existing_monthly_debt", label: "Otras cuotas al mes", kind: "eur", optional: true },
      { id: "available_savings", label: "Ahorro para invertir", kind: "eur" },
      { id: "age", label: "Edad", kind: "int" },
      { id: "residence", label: "Comunidad donde vives", kind: "region", hint: "Decide la escala autonómica del IRPF" },
      {
        id: "taxable_base",
        label: "Base liquidable general del IRPF",
        kind: "eur",
        optional: true,
        hint: "Sin el alquiler. Si no la sabes, deja este campo y rellena el tipo marginal",
      },
      { id: "marginal_rate", label: "Tipo marginal (supuesto)", kind: "pct", optional: true },
      { id: "descendant_ages", label: "Edad de tus hijos", kind: "text", optional: true, hint: "Separadas por comas" },
      {
        id: "savings_base",
        label: "Otras ganancias del ahorro el año de la venta",
        kind: "eur",
        optional: true,
        hint: "Intereses, dividendos… Si no lo sabes, déjalo vacío (0)",
      },
    ],
  },
  {
    title: "El piso",
    description: "Precio, impuestos de la compra y gastos de tenerlo.",
    fields: [
      { id: "price", label: "Precio", kind: "eur" },
      { id: "territory", label: "Municipio del piso", kind: "municipality", hint: "Decide el ITP, el IBI, la plusvalía y la regulación del alquiler" },
      { id: "purchase_date", label: "Fecha de compra", kind: "date", optional: true, hint: "Si la dejas vacía, hoy" },
      { id: "renovation", label: "Reforma", kind: "eur", optional: true },
      { id: "construction_value", label: "Valor catastral de la construcción", kind: "eur", hint: "Base de la amortización fiscal" },
      {
        id: "cadastral_value",
        label: "Valor catastral",
        kind: "eur",
        optional: true,
        hint: "Para calcular el IBI. Si tienes el recibo, deja este campo y rellena el IBI",
      },
      { id: "ibi_annual", label: "IBI al año (recibo)", kind: "eur", optional: true },
      {
        id: "cadastral_land_value",
        label: "Valor catastral del suelo",
        kind: "eur",
        optional: true,
        hint: "Viene en el recibo del IBI. Sin él no se calcula la plusvalía municipal",
      },
      { id: "deed_agreement", label: "Quién paga la escritura de compra", kind: "deed" },
      {
        id: "other_purchase_cost_rate",
        label: "Gestoría, tasación y copias",
        kind: "pct",
        hint: "% del precio. Impuestos, notaría y registro se calculan con la normativa",
      },
      { id: "community_fees_monthly", label: "Comunidad al mes", kind: "eur" },
      { id: "insurance_annual", label: "Seguros al año", kind: "eur", hint: "Hogar e impago" },
    ],
  },
  {
    title: "Hipoteca",
    description: "Las condiciones del préstamo y cuánto pueden subir los tipos.",
    fields: [
      { id: "annual_rate", label: "Tipo de interés fijo", kind: "pct" },
      { id: "rate_shock", label: "Subida de tipos en el escenario de estrés", kind: "pct", hint: "En puntos" },
      { id: "loan", label: "Préstamo", kind: "eur", optional: true, hint: "Si lo dejas vacío, la financiación máxima" },
      { id: "years", label: "Plazo en años", kind: "int", optional: true, hint: "Si lo dejas vacío, el máximo por edad" },
    ],
  },
  {
    title: "Alquiler",
    description: "Lo que cobras y la situación del contrato.",
    fields: [
      { id: "monthly_rent", label: "Renta al mes", kind: "eur" },
      { id: "vacancy_rate", label: "Meses vacío", kind: "pct", hint: "% del año" },
      { id: "management_fee_rate", label: "Gestión", kind: "pct", hint: "% de la renta; 0 si lo gestionas tú" },
      { id: "maintenance_reserve_rate", label: "Reserva de mantenimiento", kind: "pct", hint: "% de la renta" },
      { id: "contract_date", label: "Fecha del contrato", kind: "date" },
      { id: "contract", label: "Contrato", kind: "contract" },
      { id: "large_holder", label: "Eres gran tenedor", kind: "bool" },
      { id: "young_tenant", label: "Inquilino de 18 a 35 años", kind: "bool" },
      { id: "below_reference_index", label: "Renta por debajo del índice de referencia", kind: "bool" },
      { id: "recent_rehabilitation", label: "Rehabilitado en los dos últimos años", kind: "bool" },
    ],
  },
  {
    title: "Venta",
    description: "Cuándo venderías y con qué gastos.",
    fields: [
      {
        id: "appreciation_rate",
        label: "Revalorización anual",
        kind: "pct",
        optional: true,
        hint: "Vacía: escenarios del municipio (conservador, base y optimista) con el IPV del INE",
      },
      {
        id: "sale_cost_rate",
        label: "Agencia y otros gastos de venta",
        kind: "pct",
        hint: "% del precio de venta. Escritura, plusvalía e IRPF se calculan con la normativa",
      },
      { id: "horizon_years", label: "Años hasta la venta", kind: "int" },
    ],
  },
];

const FIELDS = SECTIONS.flatMap((s) => s.fields);

const EMPTY: Record<string, string> = {
  residence: "ES-13",
  territory: "ES-13-28079",
  contract: "primer-alquiler",
  deed_agreement: "ley",
  horizon_years: "10",
};

// Ejemplo para probar el simulador: el caso sintético de tests/fixtures/planes/sintetico-01.yaml.
const EXAMPLE: Record<string, string> = {
  ...EMPTY,
  net_monthly_income: "4000",
  available_savings: "90000",
  age: "40",
  taxable_base: "25000",
  price: "200000",
  purchase_date: "2026-10-28",
  renovation: "10000",
  construction_value: "80000",
  cadastral_value: "100000",
  cadastral_land_value: "40000",
  other_purchase_cost_rate: "0,5",
  community_fees_monthly: "60",
  insurance_annual: "250",
  annual_rate: "3",
  rate_shock: "2",
  years: "25",
  monthly_rent: "1000",
  vacancy_rate: "5",
  management_fee_rate: "0",
  maintenance_reserve_rate: "5",
  contract_date: "2026-11-15",
  large_holder: "false",
  appreciation_rate: "",
  sale_cost_rate: "3",
};

function parse(field: Field, raw: string | undefined): { value?: unknown; error?: string } {
  const text = (raw ?? "").trim();
  if (field.kind === "bool") return { value: text === "true" };
  if (text === "") return field.optional ? {} : { error: "Falta este dato" };
  switch (field.kind) {
    case "eur": {
      const v = amount(text);
      return v === null ? { error: "Escribe un importe, p. ej. 1200,50" } : { value: v };
    }
    case "pct": {
      const v = percentToRatio(text);
      return v === null ? { error: "Escribe un porcentaje, p. ej. 3,5" } : { value: v };
    }
    case "int":
      return /^\d+$/.test(text) ? { value: Number(text) } : { error: "Escribe un número entero" };
    case "municipality":
      return /^ES-\d{2}-\d{5}$/.test(text) ? { value: text } : { error: "Elige el municipio de la lista" };
    case "text":
      if (field.id === "descendant_ages") {
        const ages = text.split(",").map((a) => a.trim());
        return ages.every((a) => /^\d+$/.test(a))
          ? { value: ages.map(Number) }
          : { error: "Edades separadas por comas, p. ej. 2, 7" };
      }
      return { value: text };
    default:
      return { value: text };
  }
}

function buildRequest(state: Record<string, string>):
  | { request: InvestmentRequest }
  | { errors: Record<string, string> } {
  const v: Record<string, unknown> = {};
  const errors: Record<string, string> = {};
  for (const field of FIELDS) {
    const { value, error } = parse(field, state[field.id]);
    if (error) errors[field.id] = error;
    else if (value !== undefined) v[field.id] = value;
  }
  if (Object.keys(errors).length > 0) return { errors };
  const pick = (...ids: string[]) =>
    Object.fromEntries(ids.filter((id) => v[id] !== undefined).map((id) => [id, v[id]]));
  const request = {
    purchase_date: v.purchase_date ?? null,
    buyer: pick(
      "net_monthly_income", "existing_monthly_debt", "available_savings", "age", "residence",
      "taxable_base", "marginal_rate", "descendant_ages", "savings_base",
    ),
    property: pick(
      "price", "territory", "renovation", "construction_value", "cadastral_value", "ibi_annual",
      "cadastral_land_value", "deed_agreement", "other_purchase_cost_rate",
      "community_fees_monthly", "insurance_annual",
    ),
    financing: pick("annual_rate", "rate_shock", "loan", "years"),
    rental: {
      ...pick("monthly_rent", "vacancy_rate", "management_fee_rate", "maintenance_reserve_rate",
        "contract_date"),
      situation: pick("contract", "large_holder", "young_tenant", "below_reference_index",
        "recent_rehabilitation"),
    },
    exit: pick("appreciation_rate", "sale_cost_rate", "horizon_years"),
  } as unknown as InvestmentRequest;
  return { request };
}

const GROUPS: { title: string; keys: string[]; summary: string[]; topic?: string }[] = [
  {
    title: "Capacidad de compra",
    summary: ["affordability.max_price"],
    keys: ["affordability.max_price", "affordability.max_loan", "affordability.max_payment", "affordability.years"],
  },
  {
    title: "Compra",
    summary: ["purchase_costs.total", "cashflow.cash_invested"],
    keys: [
      "purchase_costs.transfer_tax", "purchase_costs.vat", "purchase_costs.stamp_duty",
      "purchase_costs.notary", "purchase_costs.registry", "purchase_costs.other",
      "purchase_costs.total", "cashflow.cash_invested",
    ],
  },
  {
    title: "Hipoteca",
    summary: ["mortgage.monthly_payment"],
    topic: "hipoteca",
    keys: ["financing.loan", "financing.years", "mortgage.monthly_payment", "mortgage.stressed_payment"],
  },
  {
    title: "Primer año de alquiler",
    topic: "explotacion",
    summary: ["cashflow.monthly_after_tax", "cashflow.gross_yield"],
    keys: [
      "cashflow.gross_yield", "holding_costs.ibi_annual", "cashflow.annual_operating",
      "cashflow.annual_tax", "cashflow.annual_after_tax", "cashflow.monthly_after_tax",
      "cashflow.cash_on_cash",
    ],
  },
  {
    title: "Plazo recomendado en estrés",
    topic: "estres",
    summary: ["term.recommended_years"],
    keys: ["term.recommended_years", "term.stressed_monthly_payment", "term.stressed_monthly_cashflow"],
  },
  {
    title: "Venta",
    summary: ["irr.rate"],
    topic: "venta",
    keys: [
      "irr.sale_price", "sale_costs.notary", "sale_costs.municipal_gains_tax",
      "irr.capital_gains_tax", "irr.net_sale_proceeds", "irr.rate",
    ],
  },
  {
    title: "Escenarios de revalorización",
    summary: ["valuation.appreciation_base"],
    keys: [
      "valuation.appreciation_conservative", "valuation.appreciation_base",
      "valuation.appreciation_optimistic", "irr.rate_conservative", "irr.rate_optimistic",
    ],
  },
];

const HEADLINE = ["cashflow.monthly_after_tax", "cashflow.cash_on_cash", "irr.rate", "term.recommended_years"];

const stepOf = (id: string) => SECTIONS.findIndex((s) => s.fields.some((f) => f.id === id));

export function Simulator() {
  const [state, setState] = useState<Record<string, string>>(EMPTY);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [step, setStep] = useState(0);
  const [result, setResult] = useState<InvestmentResponse | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [regions, setRegions] = useState<Region[]>([]);
  const results = useRef<HTMLElement>(null);
  const summary = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch("/api/profile/regions")
      .then(async (resp) => (resp.ok ? setRegions((await resp.json()) as Region[]) : null))
      .catch(() => undefined);
  }, []);

  const set = (id: string, value: string) => {
    setState((s) => ({ ...s, [id]: value }));
    if (errors[id]) setErrors(({ [id]: _, ...rest }) => rest);
  };

  /** Los errores de un paso, o de todos: al avanzar se mira solo el paso; al calcular, todos. */
  function check(sections: Section[]): Record<string, string> {
    const found: Record<string, string> = {};
    for (const field of sections.flatMap((s) => s.fields)) {
      const { error } = parse(field, state[field.id]);
      if (error) found[field.id] = error;
    }
    return found;
  }

  const form = useRef<HTMLFormElement>(null);

  /** Al cambiar de paso: el foco al paso nuevo y, si el principio del formulario quedó arriba, a la vista. */
  function go(next: number) {
    setStep(next);
    requestAnimationFrame(() => {
      document.getElementById(`paso-${next}`)?.focus({ preventScroll: true });
      const top = form.current?.getBoundingClientRect().top ?? 0;
      if (top < 0) form.current?.scrollIntoView({ block: "start", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    });
  }

  function forward() {
    const found = check([SECTIONS[step]]);
    setErrors((old) => ({ ...old, ...found }));
    if (Object.keys(found).length === 0) go(step + 1);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const built = buildRequest(state);
    if ("errors" in built) {
      setErrors(built.errors);
      setStep(stepOf(Object.keys(built.errors)[0]));
      requestAnimationFrame(() => summary.current?.focus());
      return;
    }
    setErrors({});
    setFailure(null);
    setLoading(true);
    try {
      const resp = await fetch("/api/simulate/investment", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(built.request),
      });
      const body = await resp.json();
      if (!resp.ok) {
        const detail = typeof body.detail === "string" ? body.detail : "Revisa los datos del formulario.";
        setFailure(detail);
        setResult(null);
      } else {
        setResult(body as InvestmentResponse);
        // En una columna, el resultado queda debajo del formulario: se lleva a la vista
        if (window.matchMedia("(max-width: 920px)").matches)
          requestAnimationFrame(() => results.current?.scrollIntoView({ block: "start" }));
      }
    } catch {
      setFailure("No se ha podido conectar con la API. ¿Está arrancada con make api?");
    } finally {
      setLoading(false);
    }
  }

  const section = SECTIONS[step];
  const last = step === SECTIONS.length - 1;
  const required = section.fields.filter((f) => !f.optional && f.kind !== "bool");
  const extra = section.fields.filter((f) => f.optional || f.kind === "bool");
  const wrong = Object.keys(errors);
  const stepErrors = (i: number) => SECTIONS[i].fields.filter((f) => errors[f.id]).length;

  return (
    <div className="simulator">
      <form ref={form} className="stepper" onSubmit={submit} noValidate aria-labelledby="simulador-pasos">
        <div className="stepper-head">
          <p id="simulador-pasos" className="stepper-count">
            Paso {step + 1} de {SECTIONS.length}
          </p>
          <button type="button" className="link-button" onClick={() => setState(EXAMPLE)}>
            Rellenar con un ejemplo
          </button>
        </div>
        <div className="stepper-progress" aria-hidden="true">
          <span style={{ width: `${((step + 1) / SECTIONS.length) * 100}%` }} />
        </div>
        <ol className="stepper-steps">
          {SECTIONS.map((s, i) => (
            <li key={s.title}>
              <button
                type="button"
                aria-current={i === step ? "step" : undefined}
                className={stepErrors(i) > 0 ? "has-errors" : i < step ? "is-done" : undefined}
                onClick={() => go(i)}
              >
                <span className="stepper-n" aria-hidden="true">
                  {i + 1}
                </span>
                {s.title}
                {stepErrors(i) > 0 && <span className="visually-hidden"> (con datos por corregir)</span>}
              </button>
            </li>
          ))}
        </ol>

        {wrong.length > 0 && (
          <div ref={summary} tabIndex={-1} className="error-summary">
            <Callout tone="danger">
              <p>
                <strong>
                  {wrong.length === 1 ? "Falta o no vale 1 dato." : `Faltan o no valen ${wrong.length} datos.`}
                </strong>{" "}
                {SECTIONS.map((s, i) => [s, i] as const)
                  .filter(([, i]) => stepErrors(i) > 0)
                  .map(([s, i], n) => (
                    <span key={s.title}>
                      {n > 0 && " · "}
                      <button type="button" className="link-button" onClick={() => go(i)}>
                        {s.title} ({stepErrors(i)})
                      </button>
                    </span>
                  ))}
              </p>
            </Callout>
          </div>
        )}

        <fieldset className="stepper-panel" id={`paso-${step}`} tabIndex={-1} key={section.title}>
          <legend>{section.title}</legend>
          <p className="stepper-description">{section.description}</p>
          <div className="field-grid">
            {required.map((field) => (
              <FieldInput
                key={field.id}
                field={field}
                regions={regions}
                value={state[field.id] ?? ""}
                error={errors[field.id]}
                onChange={(value) => set(field.id, value)}
              />
            ))}
          </div>
          {extra.length > 0 && (
            <details className="more-fields" open={extra.some((f) => errors[f.id] || (state[f.id] && state[f.id] !== "false"))}>
              <summary>
                Más datos <span className="more-fields-note">opcionales, afinan el cálculo</span>
              </summary>
              <div className="field-grid">
                {extra.map((field) => (
                  <FieldInput
                    key={field.id}
                    field={field}
                    regions={regions}
                    value={state[field.id] ?? ""}
                    error={errors[field.id]}
                    onChange={(value) => set(field.id, value)}
                  />
                ))}
              </div>
            </details>
          )}
        </fieldset>

        <div className="stepper-actions">
          {step > 0 && (
            <button type="button" className="secondary" onClick={() => go(step - 1)}>
              Anterior
            </button>
          )}
          {last ? (
            <button type="submit" disabled={loading} aria-busy={loading}>
              <Swap>{loading ? "Calculando…" : "Calcular el plan"}</Swap>
            </button>
          ) : (
            <button type="button" onClick={forward}>
              Siguiente: {SECTIONS[step + 1].title}
            </button>
          )}
          {!last && result && (
            <button type="submit" className="secondary" disabled={loading}>
              Recalcular
            </button>
          )}
        </div>
      </form>

      <section ref={results} className="results" aria-live="polite" aria-label="Tu plan">
        {failure && (
          <Callout tone="danger">
            <p>{failure}</p>
          </Callout>
        )}
        {loading && <Skeleton label="Calculando tu plan…" />}
        {!result && !failure && !loading && <SimulatorEmpty />}
        {result && !loading && <Results result={result} />}
      </section>
    </div>
  );
}

function SimulatorEmpty() {
  return (
    <div className="section-card simulator-empty">
      <h2>Tu plan, con tus números</h2>
      <p className="stepper-description">
        Rellena los cinco pasos, o prueba con el ejemplo, y verás antes de comprar:
      </p>
      <ul className="check-list">
        <li>cuánto puedes comprar y la cuota de tu hipoteca;</li>
        <li>lo que te queda cada mes tras gastos e impuestos, también si suben los tipos;</li>
        <li>lo que ganas al vender, con la plusvalía y el IRPF;</li>
        <li>cada cifra con su fórmula y la norma de la que sale.</li>
      </ul>
    </div>
  );
}

function FieldInput({
  field,
  regions,
  value,
  error,
  onChange,
}: {
  field: Field;
  regions: Region[];
  value: string;
  error?: string;
  onChange: (value: string) => void;
}) {
  const id = `f-${field.id}`;
  const help = error || field.hint ? `${id}-help` : undefined;
  if (field.kind === "bool") {
    return (
      <label className="check" htmlFor={id}>
        <input
          id={id}
          type="checkbox"
          checked={value === "true"}
          onChange={(e) => onChange(e.target.checked ? "true" : "false")}
        />
        {field.label}
      </label>
    );
  }
  const unit = field.kind === "eur" ? "€" : field.kind === "pct" ? "%" : null;
  return (
    <div className={`field${field.kind === "municipality" ? " wide" : ""}`}>
      <label htmlFor={id}>
        {field.label}
        {field.optional && <span className="optional"> · opcional</span>}
      </label>
      {field.kind === "region" ? (
        <select id={id} value={value} onChange={(e) => onChange(e.target.value)} aria-describedby={help}>
          {regions.length === 0 && <option value={value}>Cargando…</option>}
          {regions.map((r) => (
            <option key={r.code} value={r.code}>
              {r.name}
            </option>
          ))}
        </select>
      ) : field.kind === "municipality" ? (
        <MunicipalityPicker id={id} value={value} onChange={onChange} invalid={Boolean(error)} describedBy={help} />
      ) : field.kind === "deed" ? (
        <select id={id} value={value} onChange={(e) => onChange(e.target.value)} aria-describedby={help}>
          <option value="ley">Lo que dice la ley: el vendedor</option>
          <option value="comprador">Pacto: la pago yo</option>
          <option value="vendedor">Pacto: el vendedor</option>
        </select>
      ) : field.kind === "contract" ? (
        <select id={id} value={value} onChange={(e) => onChange(e.target.value)} aria-describedby={help}>
          <option value="primer-alquiler">Primer alquiler de la vivienda</option>
          <option value="nuevo-contrato">Nuevo contrato (ya estuvo alquilada)</option>
          <option value="prorroga-tacita">Prórroga tácita</option>
        </select>
      ) : (
        <div className={unit ? "input-affix" : undefined}>
          <input
            id={id}
            type={field.kind === "date" ? "date" : "text"}
            inputMode={field.kind === "eur" || field.kind === "pct" ? "decimal" : field.kind === "int" ? "numeric" : undefined}
            value={value}
            aria-invalid={error ? true : undefined}
            aria-describedby={help}
            onChange={(e) => onChange(e.target.value)}
          />
          {unit && (
            <span className="affix" aria-hidden="true">
              {unit}
            </span>
          )}
        </div>
      )}
      {(error || field.hint) && (
        <small id={help} className={error ? "error" : "hint"}>
          {error ?? field.hint}
        </small>
      )}
    </div>
  );
}

function Results({ result }: { result: InvestmentResponse }) {
  const f = result.figures;
  const figures = new Map(Object.entries(f));
  const scenario = result.pending_scenario;
  return (
    <>
      <Points items={notePoints(result.warnings, "warning")} label="Avisos del cálculo" />
      <section className="verdict" aria-labelledby="simulador-veredicto">
        <div className="verdict-head">
          <h2 id="simulador-veredicto">Tu plan</h2>
        </div>
        <div className="verdict-figures">
          {HEADLINE.filter((k) => f[k]).map((k) => (
            <VerdictFigure key={k} figure={f[k]} />
          ))}
        </div>
      </section>
      {!f["irr.rate"] && result.no_irr_reason && (
        <p className="hint">Sin TIR: {result.no_irr_reason}</p>
      )}
      <div className="plan-blocks">
        {GROUPS.map((group) => (
          <FigureBlock
            key={group.title}
            id={group.title}
            title={group.title}
            figures={group.keys.filter((k) => f[k]).map((k) => f[k])}
            keys={group.summary}
          >
            {group.topic && (
              <TopicCharts topic={group.topic} figures={figures} series={result.series} breakdown={result.breakdown} />
            )}
          </FigureBlock>
        ))}
      </div>
      <Points items={notePoints(result.appreciation_notes)} label="Notas de la revalorización" />
      <div className="group">
        <h3>Si se convalidan las normas pendientes</h3>
        {scenario.changes.length === 0 ? (
          <p className="empty">Las normas pendientes de convalidación no cambian tu plan.</p>
        ) : (
          <>
            <Lede>Si se convalidan, estas cifras de tu plan cambian así:</Lede>
            <Changes
              rows={scenario.changes.map((c) => ({
                key: c.key,
                label: label(c.key),
                before: formatValue(c.base.value, c.base.unit),
                after: formatValue(c.scenario.value, c.scenario.unit),
              }))}
            />
            <ExplainHead>Las normas que entrarían</ExplainHead>
            <SourceList sources={scenario.new_rules} />
          </>
        )}
      </div>
    </>
  );
}
