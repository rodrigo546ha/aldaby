"use client";

import { useCallback, useEffect, useState, type ChangeEvent, type FormEvent } from "react";

import type { components } from "../lib/api-types";
import { formatDate, formatValue, PROPERTY_TYPE } from "../lib/format";
import { AppLink, DATA } from "./AppLink";

type Feed = components["schemas"]["FeedOut"];
type Listing = components["schemas"]["ListingOut"];

// Feeds XML de agencias (ADR-0038): el profesional da de alta el de una agencia con su
// consentimiento; la cartera la lee el trabajo diario y entra en la búsqueda.

const EMPTY = { agency_name: "", url: "", scope: "organizacion", consent_on: "", consent_ref: "" };

export function Feeds() {
  const [feeds, setFeeds] = useState<Feed[]>([]);
  const [listings, setListings] = useState<Listing[]>([]);
  const [failure, setFailure] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [f, l] = await Promise.all([fetch("/api/feeds"), fetch("/api/feeds/listings")]);
      if (!f.ok || !l.ok) {
        const body = await (f.ok ? l : f).json().catch(() => ({}));
        setFailure(typeof body.detail === "string" ? body.detail : "No se han podido cargar los feeds.");
        return;
      }
      setFeeds((await f.json()) as Feed[]);
      setListings((await l.json()) as Listing[]);
    } catch {
      setFailure("No se ha podido conectar con la API. ¿Está arrancada con make api?");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function remove(feed: Feed) {
    if (!window.confirm(`¿Dejar de leer el feed de ${feed.agency_name}? Sus inmuebles se retiran.`)) {
      return;
    }
    const resp = await fetch(`/api/feeds/${feed.id}`, { method: "DELETE" });
    if (resp.ok) await load();
  }

  return (
    <div className="feeds">
      {failure && <p className="failure" role="alert">{failure}</p>}
      <section>
        <h2>Feeds de agencias</h2>
        {feeds.length === 0 ? (
          <div className="section-card empty-card">
            <p>
              <strong>Aún no hay ningún feed.</strong> Con el consentimiento por escrito de una agencia, su CRM publica un
              enlace XML con sus inmuebles en venta. Lo das de alta abajo y cada mañana se leen y se analizan en la búsqueda
              de tus clientes.
            </p>
          </div>
        ) : (
          <ul className="feed-list">
            {feeds.map((f) => (
              <li key={f.id}>
                <span className="feed-name">{f.agency_name}</span>
                <span className="hint">
                  {f.scope === "todos" ? "La ven todos los usuarios" : "Solo tu organización"} ·
                  consentimiento del {formatDate(f.consent_on)} ({f.consent_ref})
                </span>
                <span className="hint">{runSummary(f)}</span>
                <span className="feed-actions">
                  <button type="button" className="link danger" onClick={() => void remove(f)}>
                    Dar de baja
                  </button>
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
      <NewFeed onCreated={load} />
      <section>
        <h2>Cartera de las agencias</h2>
        <p className="hint">
          Inmuebles en venta de los feeds que puedes ver. Los datos los da la agencia; los que no
          tienen coordenada ni referencia catastral no se pueden ubicar ni entrar en la búsqueda.
        </p>
        {listings.length === 0 ? (
          <p className="empty">Todavía no hay inmuebles: el feed se lee una vez al día.</p>
        ) : (
          <table className="listings">
            <thead>
              <tr>
                <th scope="col">Inmueble</th>
                <th scope="col">Tipo</th>
                <th scope="col">Precio</th>
                <th scope="col">Superficie</th>
                <th scope="col">Agencia</th>
                <th scope="col">Plan</th>
              </tr>
            </thead>
            <tbody>
              {listings.map((x) => (
                <tr key={x.id}>
                  <td>
                    {x.url ? (
                      <a href={x.url} target="_blank" rel="noopener noreferrer">
                        {x.title ?? "Inmueble"}
                      </a>
                    ) : (
                      x.title ?? "Inmueble"
                    )}
                    {x.province && x.province !== x.municipality && (
                      <span className="hint"> · {x.province}</span>
                    )}
                  </td>
                  <td>{x.property_type ? PROPERTY_TYPE[x.property_type] ?? x.property_type : "—"}</td>
                  <td className="number">
                    {x.asking_price != null ? formatValue(String(x.asking_price), "EUR") : "—"}
                  </td>
                  <td className="number">{x.built_area_m2 != null ? `${x.built_area_m2} m²` : "—"}</td>
                  <td>{x.agency?.replace(/^Feed de /, "") ?? "—"}</td>
                  <td>
                    {x.located && x.section_code && x.property_type === "vivienda" ? (
                      <AppLink href={`/plan/${x.id}`} data={DATA.plan(x.id)}>Ver el plan</AppLink>
                    ) : (
                      <span className="hint">
                        {x.property_type !== "vivienda" ? "No es vivienda" : "Sin ubicar"}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

function runSummary(f: Feed): string {
  if (!f.last_run_at) return "Pendiente de la primera lectura (cada mañana)";
  const when = formatDate(f.last_run_at.slice(0, 10));
  if (f.error) return `Última lectura ${when}: ${f.error}`;
  const parts = [`${f.listings ?? 0} en venta`];
  if (f.without_location) parts.push(`${f.without_location} sin ubicar`);
  if (f.retired) parts.push(`${f.retired} retirados`);
  return `Última lectura ${when}: ${parts.join(", ")}`;
}

function NewFeed({ onCreated }: { onCreated: () => Promise<void> }) {
  const [form, setForm] = useState(EMPTY);
  const [consent, setConsent] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const field = (id: keyof typeof EMPTY) => ({
    id: `feed-${id}`,
    value: form[id],
    onChange: (e: ChangeEvent<HTMLInputElement>) => setForm((f) => ({ ...f, [id]: e.target.value })),
  });

  async function submit(event: FormEvent) {
    event.preventDefault();
    setFailure(null);
    setBusy(true);
    try {
      const resp = await fetch("/api/feeds", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...form, consent_confirmed: consent }),
      });
      const body = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        setFailure(typeof body.detail === "string" ? body.detail : "No se ha podido dar de alta el feed");
        return;
      }
      setForm(EMPTY);
      setConsent(false);
      await onCreated();
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="feed-form" onSubmit={submit}>
      <fieldset>
        <legend>Dar de alta un feed</legend>
        <p className="hint">
          El enlace XML que genera el CRM de la agencia en formato Kyero (Witei, Sooprema, Casafari…).
          Se guarda cifrado y no se vuelve a mostrar.
        </p>
        <div className="field">
          <label htmlFor="feed-agency_name">Agencia</label>
          <input required maxLength={120} {...field("agency_name")} />
        </div>
        <div className="field">
          <label htmlFor="feed-url">Enlace del feed</label>
          <input required type="password" autoComplete="off" placeholder="https://…" {...field("url")} />
        </div>
        <div className="field">
          <label htmlFor="feed-scope">Quién verá sus inmuebles</label>
          <select
            id="feed-scope"
            value={form.scope}
            onChange={(e) => setForm((f) => ({ ...f, scope: e.target.value }))}
          >
            <option value="organizacion">Solo mi organización</option>
            <option value="todos">Todos los usuarios de la herramienta</option>
          </select>
          <span className="hint">«Todos» solo si la agencia lo ha autorizado expresamente.</span>
        </div>
        <div className="field">
          <label htmlFor="feed-consent_on">Fecha del consentimiento</label>
          <input required type="date" {...field("consent_on")} />
        </div>
        <div className="field">
          <label htmlFor="feed-consent_ref">Documento firmado</label>
          <input required maxLength={300} placeholder="Contrato de alta, anexo…" {...field("consent_ref")} />
        </div>
        <label className="check">
          <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
          Tengo el consentimiento por escrito de la agencia para que la herramienta lea y muestre su
          cartera con ese alcance.
        </label>
        {failure && <p className="failure" role="alert">{failure}</p>}
        <button type="submit" disabled={busy || !consent}>
          Dar de alta
        </button>
      </fieldset>
    </form>
  );
}
