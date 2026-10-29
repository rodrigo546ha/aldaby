"use client";

import { useState, type FormEvent } from "react";

import type { components } from "../lib/api-types";
import { amount, formatValue, label, percentToRatio } from "../lib/format";
import { FigureView } from "./FigureView";

type InvestmentRequest = components["schemas"]["InvestmentRequest"];
type InvestmentResponse = components["schemas"]["InvestmentResponse"];

type Kind = "eur" | "pct" | "int" | "text" | "date" | "bool" | "contract" | "deed";
type Field = { id: string; label: string; kind: Kind; hint?: string; optional?: boolean };
type Section = { title: string; fields: Field[] };

const SECTIONS: Section[] = [
  {
    title: "Tú",
    fields: [
      { id: "net_monthly_income", label: "Ingresos netos al mes", kind: "eur" },
      { id: "existing_monthly_debt", label: "Otras cuotas al mes", kind: "eur", optional: true },
      { id: "available_savings", label: "Ahorro para invertir", kind: "eur" },
      { id: "age", label: "Edad", kind: "int" },
      { id: "residence", label: "Comunidad de residencia", kind: "text", hint: "Código INE: ES-13 es Madrid" },
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
    fields: [
      { id: "price", label: "Precio", kind: "eur" },
      { id: "territory", label: "Municipio", kind: "text", hint: "Código INE: ES-13-28079 es Madrid capital" },
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
    fields: [
      { id: "annual_rate", label: "Tipo de interés fijo", kind: "pct" },
      { id: "rate_shock", label: "Subida de tipos en el escenario de estrés", kind: "pct", hint: "En puntos" },
      { id: "loan", label: "Préstamo", kind: "eur", optional: true, hint: "Si lo dejas vacío, la financiación máxima" },
      { id: "years", label: "Plazo en años", kind: "int", optional: true, hint: "Si lo dejas vacío, el máximo por edad" },
    ],
  },
  {
    title: "Alquiler",
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
    fields: [
      { id: "appreciation_rate", label: "Revalorización anual (supuesto)", kind: "pct" },
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
  appreciation_rate: "2",
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

const GROUPS: { title: string; keys: string[] }[] = [
  {
    title: "Capacidad de compra",
    keys: ["affordability.max_price", "affordability.max_loan", "affordability.max_payment", "affordability.years"],
  },
  {
    title: "Compra",
    keys: [
      "purchase_costs.transfer_tax", "purchase_costs.vat", "purchase_costs.stamp_duty",
      "purchase_costs.notary", "purchase_costs.registry", "purchase_costs.other",
      "purchase_costs.total", "cashflow.cash_invested",
    ],
  },
  {
    title: "Hipoteca",
    keys: ["financing.loan", "financing.years", "mortgage.monthly_payment", "mortgage.stressed_payment"],
  },
  {
    title: "Primer año de alquiler",
    keys: [
      "cashflow.gross_yield", "holding_costs.ibi_annual", "cashflow.annual_operating",
      "cashflow.annual_tax", "cashflow.monthly_after_tax", "cashflow.cash_on_cash",
    ],
  },
  {
    title: "Plazo recomendado en estrés",
    keys: ["term.recommended_years", "term.stressed_monthly_payment", "term.stressed_monthly_cashflow"],
  },
  {
    title: "Venta",
    keys: [
      "irr.sale_price", "sale_costs.notary", "sale_costs.municipal_gains_tax",
      "irr.capital_gains_tax", "irr.net_sale_proceeds", "irr.rate",
    ],
  },
];

const HEADLINE = ["cashflow.monthly_after_tax", "cashflow.cash_on_cash", "irr.rate", "term.recommended_years"];

export function Simulator() {
  const [state, setState] = useState<Record<string, string>>(EMPTY);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [result, setResult] = useState<InvestmentResponse | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const set = (id: string, value: string) => setState((s) => ({ ...s, [id]: value }));

  async function submit(event: FormEvent) {
    event.preventDefault();
    const built = buildRequest(state);
    if ("errors" in built) {
      setErrors(built.errors);
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
      }
    } catch {
      setFailure("No se ha podido conectar con la API. ¿Está arrancada con make api?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="simulator">
      <form onSubmit={submit} noValidate>
        {SECTIONS.map((section) => (
          <fieldset key={section.title}>
            <legend>{section.title}</legend>
            {section.fields.map((field) => (
              <FieldInput
                key={field.id}
                field={field}
                value={state[field.id] ?? ""}
                error={errors[field.id]}
                onChange={(value) => set(field.id, value)}
              />
            ))}
          </fieldset>
        ))}
        <div className="actions">
          <button type="submit" disabled={loading}>
            {loading ? "Calculando…" : "Calcular el plan"}
          </button>
          <button type="button" className="secondary" onClick={() => setState(EXAMPLE)}>
            Rellenar con un ejemplo
          </button>
        </div>
      </form>

      <section className="results" aria-live="polite">
        {failure && <p className="failure">{failure}</p>}
        {!result && !failure && (
          <p className="empty">Rellena tus datos y los del piso para ver tu plan.</p>
        )}
        {result && <Results result={result} />}
      </section>
    </div>
  );
}

function FieldInput({
  field,
  value,
  error,
  onChange,
}: {
  field: Field;
  value: string;
  error?: string;
  onChange: (value: string) => void;
}) {
  const id = `f-${field.id}`;
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
  return (
    <div className="field">
      <label htmlFor={id}>
        {field.label}
        {field.kind === "eur" && <span className="unit"> (€)</span>}
        {field.kind === "pct" && <span className="unit"> (%)</span>}
      </label>
      {field.kind === "deed" ? (
        <select id={id} value={value} onChange={(e) => onChange(e.target.value)}>
          <option value="ley">Lo que dice la ley: el vendedor</option>
          <option value="comprador">Pacto: la pago yo</option>
          <option value="vendedor">Pacto: el vendedor</option>
        </select>
      ) : field.kind === "contract" ? (
        <select id={id} value={value} onChange={(e) => onChange(e.target.value)}>
          <option value="primer-alquiler">Primer alquiler de la vivienda</option>
          <option value="nuevo-contrato">Nuevo contrato (ya estuvo alquilada)</option>
          <option value="prorroga-tacita">Prórroga tácita</option>
        </select>
      ) : (
        <input
          id={id}
          type={field.kind === "date" ? "date" : "text"}
          inputMode={field.kind === "eur" || field.kind === "pct" ? "decimal" : field.kind === "int" ? "numeric" : undefined}
          value={value}
          aria-invalid={error ? true : undefined}
          aria-describedby={error || field.hint ? `${id}-help` : undefined}
          onChange={(e) => onChange(e.target.value)}
        />
      )}
      {(error || field.hint) && (
        <small id={`${id}-help`} className={error ? "error" : "hint"}>
          {error ?? field.hint}
        </small>
      )}
    </div>
  );
}

function Results({ result }: { result: InvestmentResponse }) {
  const f = result.figures;
  const scenario = result.pending_scenario;
  return (
    <>
      {result.warnings.length > 0 && (
        <ul className="warnings">
          {result.warnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      )}
      <div className="headline">
        {HEADLINE.filter((k) => f[k]).map((k) => (
          <FigureView key={k} figure={f[k]} />
        ))}
        {!f["irr.rate"] && result.no_irr_reason && (
          <div className="figure">
            <span className="figure-label">TIR</span>
            <div className="figure-value small">Sin TIR: {result.no_irr_reason}</div>
          </div>
        )}
      </div>
      {GROUPS.map((group) => (
        <div key={group.title} className="group">
          <h3>{group.title}</h3>
          <div className="grid">
            {group.keys.filter((k) => f[k]).map((k) => (
              <FigureView key={k} figure={f[k]} />
            ))}
          </div>
        </div>
      ))}
      <div className="group">
        <h3>Si se aprueban las normas pendientes</h3>
        {scenario.changes.length === 0 ? (
          <p className="empty">Las normas pendientes de convalidación no cambian tu plan.</p>
        ) : (
          <>
            <p>
              Normas que entrarían: {scenario.new_rules.map((r) => r.id).join(", ")}.
            </p>
            <table>
              <thead>
                <tr>
                  <th>Cifra</th>
                  <th>Hoy</th>
                  <th>Con las normas pendientes</th>
                  <th>Diferencia</th>
                </tr>
              </thead>
              <tbody>
                {scenario.changes.map((c) => (
                  <tr key={c.key}>
                    <td>{label(c.key)}</td>
                    <td>{formatValue(c.base.value, c.base.unit)}</td>
                    <td>{formatValue(c.scenario.value, c.scenario.unit)}</td>
                    <td>{formatValue(c.delta.value, c.delta.unit)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>
    </>
  );
}
