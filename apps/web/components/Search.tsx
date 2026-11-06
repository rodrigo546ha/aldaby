"use client";

import { useEffect, useState, type FormEvent } from "react";

import type { components } from "../lib/api-types";
import { percentToRatio } from "../lib/format";
import { Callout } from "./Icon";
import { AppLink, DATA } from "./AppLink";
import { invalidatePlans } from "../lib/data";
import { Swap } from "./Motion";

type ProfileOut = components["schemas"]["ProfileOut"];

// Supuestos de la búsqueda inversa (F6.5, ADR-0023). Las ofertas, con el plan del usuario en cada
// una, están en el mapa (ADR-0054): aquí solo lo que el usuario pone y no tiene fuente pública.
const ASSUMPTIONS: { id: string; label: string; kind: "pct" | "eur" | "bool"; hint?: string }[] = [
  { id: "vacancy_rate", label: "Tiempo vacío al año", kind: "pct", hint: "Del año: el tiempo sin inquilino entre contratos" },
  { id: "management_fee_rate", label: "Gestión si la delegas", kind: "pct", hint: "De la renta que cobras" },
  { id: "other_purchase_cost_rate", label: "Gestoría y tasación", kind: "pct", hint: "Del precio de compra" },
  { id: "sale_cost_rate", label: "Gastos de venta", kind: "pct", hint: "Del precio de venta: agencia y otros" },
  { id: "min_monthly_cashflow", label: "Cash flow mínimo al mes", kind: "eur", hint: "Lo que quieres que te quede como poco. Vacío, 0 €" },
  { id: "large_holder", label: "¿Tienes más de diez viviendas?", kind: "bool" },
];

export function Search() {
  const [profile, setProfile] = useState<ProfileOut | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch("/api/profile/current")
      .then(async (resp) => {
        const body = await resp.json().catch(() => ({}));
        if (resp.ok) setProfile(body as ProfileOut);
        else setFailure(resp.status === 404 ? "Confirma primero tu perfil." : String(body.detail ?? "Error"));
      })
      .catch(() => setFailure("No se ha podido conectar con la API."));
  }, []);

  if (failure)
    return (
      <section className="section-card assumptions-page">
        <Callout tone="info">
          <p>{failure}</p>
        </Callout>
        <div className="actions">
          <AppLink className="button-link primary" href="/perfil">
            Ir al perfil
          </AppLink>
        </div>
      </section>
    );
  if (!profile) return null;
  return (
    <div className="assumptions-page">
      <Assumptions profile={profile} onSaved={() => setSaved(true)} />
      <div role="status">
        {saved && (
          <Callout tone="success">
            <p>
              <strong>Guardados.</strong> Tu plan en cada oferta ya los usa. <AppLink href="/mapa" data={DATA.map()}>Ver las ofertas</AppLink>
            </p>
          </Callout>
        )}
      </div>
    </div>
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
    if (resp.ok) invalidatePlans(); // tus supuestos cambian el plan de cada oferta
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      setError(typeof body.detail === "string" ? body.detail : "No se han podido guardar");
      return;
    }
    onSaved();
  }

  return (
    <form className="section-card assumptions" onSubmit={save} aria-labelledby="assumptions-title">
      <header>
        <h2 id="assumptions-title">Alquiler, compra y venta</h2>
        <p>El tipo de la hipoteca, el IBI, la comunidad, los seguros y el mantenimiento ya se estiman con datos oficiales.</p>
      </header>
      <div className="field-grid">
      {ASSUMPTIONS.map((a) => (
        <div className="field" key={a.id}>
          <label htmlFor={`assumption-${a.id}`}>
            {a.label}
            {profile.missing_search.includes(a.id) && <span className="tag danger field-tag">Falta</span>}
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
            <div className="input-affix">
              <input
                id={`assumption-${a.id}`}
                inputMode="decimal"
                value={values[a.id] ?? ""}
                aria-describedby={`assumption-${a.id}-hint`}
                onChange={(e) => setValues((v) => ({ ...v, [a.id]: e.target.value }))}
              />
              <span className="affix" aria-hidden="true">
                {a.kind === "pct" ? "%" : "€"}
              </span>
            </div>
          )}
          {a.hint && (
            <small id={`assumption-${a.id}-hint`} className="hint">
              {a.hint}
            </small>
          )}
        </div>
      ))}
      </div>
      {error && (
        <Callout tone="danger">
          <p>{error}</p>
        </Callout>
      )}
      <div className="actions">
        <button type="submit" disabled={saving}>
          <Swap>{saving ? "Guardando…" : "Guardar"}</Swap>
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
