"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import type { components } from "../lib/api-types";
import { amount, percentToRatio } from "../lib/format";
import { FigureView } from "./FigureView";

type SearchOut = components["schemas"]["SearchOut"];
type ScoredOut = components["schemas"]["ScoredOut"];
type ProfileOut = components["schemas"]["ProfileOut"];
type RentalAdviceOut = components["schemas"]["RentalAdviceOut"];
type RentalTypeOut = components["schemas"]["RentalTypeOut"];

// Búsqueda inversa (F6.5, ADR-0023): el plan del usuario en cada oferta; el orden lo hace la API.
const ASSUMPTIONS: { id: string; label: string; kind: "pct" | "eur" | "bool"; hint?: string }[] = [
  { id: "vacancy_rate", label: "Meses vacío al año", kind: "pct", hint: "% del año" },
  { id: "management_fee_rate", label: "Gestión si la delegas", kind: "pct", hint: "% de la renta" },
  { id: "other_purchase_cost_rate", label: "Gestoría y tasación", kind: "pct", hint: "% del precio" },
  { id: "sale_cost_rate", label: "Gastos de venta", kind: "pct", hint: "% del precio" },
  { id: "min_monthly_cashflow", label: "Cash flow mínimo al mes", kind: "eur", hint: "€; vacío = 0" },
  { id: "large_holder", label: "¿Tienes más de diez viviendas?", kind: "bool" },
];
const SHOWN = [
  "offer.price",
  "valuation.rent_monthly",
  "cashflow.monthly_after_tax",
  "search.stressed_cashflow",
  "irr.rate",
  "cashflow.cash_invested",
];

export function Search() {
  const [profile, setProfile] = useState<ProfileOut | null>(null);
  const [result, setResult] = useState<SearchOut | null>(null);
  const [missing, setMissing] = useState<string[]>([]);
  const [failure, setFailure] = useState<string | null>(null);
  const [busy, setBusy] = useState(true);

  const load = useCallback(async () => {
    setBusy(true);
    setFailure(null);
    setMissing([]);
    try {
      const current = await fetch("/api/profile/current");
      if (!current.ok) {
        const body = await current.json().catch(() => ({}));
        setFailure(current.status === 404 ? "Confirma primero tu perfil en /perfil." : body.detail);
        setBusy(false);
        return;
      }
      setProfile((await current.json()) as ProfileOut);
      const found = await fetch("/api/search");
      const body = await found.json().catch(() => ({}));
      if (found.ok) setResult(body as SearchOut);
      else if (found.status === 422 && Array.isArray(body.detail)) setMissing(body.detail);
      else setFailure(typeof body.detail === "string" ? body.detail : "Error en la búsqueda");
    } catch {
      setFailure("No se ha podido conectar con la API. ¿Está arrancada con make api?");
    }
    setBusy(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Nivel gratuito de un particular (ADR-0040): cuántos planes completos le quedan
  const [plansLeft, setPlansLeft] = useState<number | null>(null);
  useEffect(() => {
    fetch("/api/auth/me")
      .then(async (resp) => (resp.ok ? setPlansLeft((await resp.json()).free_plans_left ?? null) : null))
      .catch(() => undefined);
  }, []);

  return (
    <div className="search">
      {profile && <Assumptions profile={profile} onSaved={load} />}
      <section className="results" aria-live="polite" aria-labelledby="ranking-title">
        <h2 id="ranking-title">Ofertas para ti</h2>
        {plansLeft !== null && (
          <p className="hint">
            {plansLeft === 0
              ? "Has usado los planes completos del nivel gratuito: puedes volver a abrir esos."
              : `Te ${plansLeft === 1 ? "queda 1 plan completo" : `quedan ${plansLeft} planes completos`} en el nivel gratuito. Volver a abrir uno no gasta otro.`}
          </p>
        )}
        {busy && <p className="empty">Calculando tu plan en cada oferta…</p>}
        {failure && <p className="failure">{failure}</p>}
        {missing.length > 0 && (
          <ul className="warnings">
            {missing.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        )}
        {result && !busy && <Ranking result={result} onReload={load} />}
      </section>
    </div>
  );
}

function Ranking({ result, onReload }: { result: SearchOut; onReload: () => void }) {
  return (
    <>
      <div className="grid">
        {result.market.map((f) => (
          <FigureView key={f.key} figure={f} />
        ))}
      </div>
      {result.ranked.length === 0 && (
        <p className="empty">No hay ofertas que se puedan puntuar todavía.</p>
      )}
      <ol className="ranking">
        {result.ranked.map((s) => (
          <OfferCard key={s.offer_id} scored={s} onReload={onReload} />
        ))}
      </ol>
      {result.skipped.length > 0 && (
        <details className="hint">
          <summary>{result.skipped.length} ofertas sin puntuar</summary>
          <ul>
            {result.skipped.map((s) => (
              <li key={s.offer_id}>
                {s.title ?? "Oferta"}: {s.reason}
              </li>
            ))}
          </ul>
        </details>
      )}
      <ul className="warnings">
        {result.notes.map((n) => (
          <li key={n}>{n}</li>
        ))}
      </ul>
    </>
  );
}

function OfferCard({ scored, onReload }: { scored: ScoredOut; onReload: () => void }) {
  const byKey = new Map(scored.figures.map((f) => [f.key, f]));
  const assumptions = scored.figures.filter((f) => f.key.startsWith("assumption."));
  return (
    <li className="offer-card">
      <div className="offer-head">
        <h3>
          {scored.title ?? (scored.kind === "enlace" ? "Oferta pegada" : "Lote del BOE")}
        </h3>
        <span className={scored.passes ? "status pass" : "status fail"}>
          {scored.passes ? "Encaja" : "No encaja"}
          {scored.auction ? " · subasta" : ""}
        </span>
        {scored.url && (
          <a href={scored.url} target="_blank" rel="noreferrer">
            Ver la oferta
          </a>
        )}
        <a href={`/plan/${scored.offer_id}`}>Ver el plan completo</a>
      </div>
      {scored.reasons.length > 0 && (
        <ul className="warnings">
          {scored.reasons.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      )}
      <div className="grid">
        {SHOWN.map((key) => {
          const f = byKey.get(key);
          return f ? <FigureView key={key} figure={f} /> : null;
        })}
      </div>
      {scored.advice && (
        <RentalAdvice offerId={scored.offer_id} advice={scored.advice} onSaved={onReload} />
      )}
      <details>
        <summary>Supuestos estimados para esta oferta</summary>
        <div className="grid">
          {assumptions.map((f) => (
            <FigureView key={f.key} figure={f} />
          ))}
        </div>
      </details>
      {scored.notes.length > 0 && (
        <details>
          <summary>Avisos</summary>
          <ul className="warnings">
            {scored.notes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </details>
      )}
    </li>
  );
}

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

function RentalAdvice({
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
      <h4>
        {advice.recommended
          ? `Cómo alquilarla: ${RENTAL_LABEL[advice.recommended].toLowerCase()}`
          : "Cómo alquilarla"}
      </h4>
      <ul className="hint">
        {advice.reasons.map((r) => (
          <li key={r}>{r}</li>
        ))}
      </ul>
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
        <details>
          <summary>Si se convalidan las normas pendientes</summary>
          <ul className="warnings">
            {advice.scenario.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </details>
      )}
      <ul className="warnings">
        {advice.notes.map((n) => (
          <li key={n}>{n}</li>
        ))}
      </ul>
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
      <p className="hint">{type.management_reason}</p>
      <div className="grid">
        {type.figures.map((f) => (
          <FigureView key={f.key} figure={f} title={FIGURE_TITLE[f.key.split(".")[2]]} />
        ))}
      </div>
      {type.notes.length > 0 && (
        <ul className="warnings">
          {type.notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      )}
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
      <p className="hint">{type.regime}</p>
      {type.requirements.length > 0 && (
        <ul className="requirements">
          {type.requirements.map((r) => (
            <li key={r.code}>
              {r.description}{" "}
              <a href={r.source_url} target="_blank" rel="noreferrer">
                fuente
              </a>
            </li>
          ))}
        </ul>
      )}
    </details>
  );
}

function Assumptions({ profile, onSaved }: { profile: ProfileOut; onSaved: () => void }) {
  const [values, setValues] = useState<Record<string, string>>(() => initial(profile));
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function save(event: FormEvent) {
    event.preventDefault();
    const out: Record<string, unknown> = {};
    for (const a of ASSUMPTIONS) {
      const raw = values[a.id]?.trim() ?? "";
      if (!raw) continue;
      if (a.kind === "pct") {
        const r = percentToRatio(raw);
        if (r === null) {
          setError(`«${a.label}» tiene que ser un porcentaje (por ejemplo 5 o 5,5)`);
          return;
        }
        out[a.id] = r;
      } else if (a.kind === "eur") out[a.id] = raw.replace(/\./g, "").replace(",", ".");
      else out[a.id] = raw;
    }
    setSaving(true);
    setError(null);
    const resp = await fetch("/api/profile/current/search", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ values: out }),
    });
    setSaving(false);
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      setError(typeof body.detail === "string" ? body.detail : "No se han podido guardar");
      return;
    }
    onSaved();
  }

  return (
    <form className="assumptions" onSubmit={save} aria-labelledby="assumptions-title">
      <h2 id="assumptions-title">Tus supuestos de búsqueda</h2>
      <p className="hint">
        No hay fuente pública para estos: los pones tú. El tipo de la hipoteca, el IBI, la
        comunidad, los seguros y el mantenimiento se estiman con datos oficiales.
      </p>
      {ASSUMPTIONS.map((a) => (
        <div className="field" key={a.id}>
          <label htmlFor={`assumption-${a.id}`}>
            {a.label}
            {profile.missing_search.includes(a.id) && <span className="origin"> · falta</span>}
          </label>
          {a.kind === "bool" ? (
            <select
              id={`assumption-${a.id}`}
              value={values[a.id] ?? ""}
              onChange={(e) => setValues((v) => ({ ...v, [a.id]: e.target.value }))}
            >
              <option value="">Sin decir</option>
              <option value="no">No</option>
              <option value="sí">Sí</option>
            </select>
          ) : (
            <input
              id={`assumption-${a.id}`}
              inputMode="decimal"
              value={values[a.id] ?? ""}
              placeholder={a.hint}
              onChange={(e) => setValues((v) => ({ ...v, [a.id]: e.target.value }))}
            />
          )}
        </div>
      ))}
      {error && <p className="failure">{error}</p>}
      <div className="actions">
        <button type="submit" disabled={saving}>
          {saving ? "Guardando…" : "Guardar y buscar"}
        </button>
      </div>
    </form>
  );
}

function initial(profile: ProfileOut): Record<string, string> {
  const out: Record<string, string> = {};
  for (const a of ASSUMPTIONS) {
    const v = profile.values[a.id];
    if (v === null || v === undefined) continue;
    if (a.kind === "pct") out[a.id] = ratioToPercent(String(v));
    else if (a.kind === "bool") out[a.id] = v ? "sí" : "no";
    else out[a.id] = String(v).replace(".", ",");
  }
  return out;
}

/** "0.055" (tanto por uno) → "5,5" (por ciento), moviendo la coma en el texto, sin floats. */
function ratioToPercent(text: string): string {
  const [int, frac = ""] = text.split(".");
  const digits = (int.replace(/^0+/, "") + frac.padEnd(2, "0")).replace(/^0+(?=\d)/, "");
  const cut = digits.length - Math.max(frac.length - 2, 0);
  const whole = digits.slice(0, cut) || "0";
  const decimals = digits.slice(cut).replace(/0+$/, "");
  return decimals ? `${whole},${decimals}` : whole;
}
