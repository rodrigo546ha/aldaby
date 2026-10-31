"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import type { components } from "../lib/api-types";
import { LISTING_LABELS, ORIGIN, spanishNumber } from "../lib/format";
import { FigureView } from "./FigureView";

type OfferOut = components["schemas"]["OfferOut"];
type OfferSummary = components["schemas"]["OfferSummary"];
type FieldOut = components["schemas"]["FieldOut"];
type AuctionNotice = components["schemas"]["AuctionNoticeOut"];
type OfferValuation = components["schemas"]["OfferValuationOut"];

const STATUS: Record<string, string> = {
  pendiente: "Extrayendo",
  extraida: "Por confirmar",
  confirmada: "Confirmada",
};
const POLL_MS = 5000;
const NOTICES_SHOWN = 10;
const VALUATION_GROUPS = [
  {
    title: "Frente al anuncio",
    keys: ["offer.asking_gap", "offer.gross_yield_at_asking", "offer.asking_rent_gap"],
  },
  { title: "Renta", keys: ["valuation.rent_monthly", "valuation.rent_m2_month"] },
  {
    title: "Precio",
    keys: ["valuation.price_total", "valuation.price_m2", "valuation.price_rent_ratio"],
  },
  {
    title: "Revalorización a 10 años",
    keys: [
      "valuation.appreciation_conservative",
      "valuation.appreciation_base",
      "valuation.appreciation_optimistic",
    ],
  },
];

export function Offers() {
  const [offers, setOffers] = useState<OfferSummary[]>([]);
  const [selected, setSelected] = useState<OfferOut | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [auctions, setAuctions] = useState<AuctionNotice[]>([]);
  // Subasta del BOE cuyo texto va a pegar el usuario: su enlace acompaña al texto.
  const [pasteFor, setPasteFor] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const resp = await fetch("/api/offers");
      if (resp.ok) setOffers((await resp.json()) as OfferSummary[]);
      const notices = await fetch("/api/offers/auctions");
      if (notices.ok) setAuctions((await notices.json()) as AuctionNotice[]);
    } catch {
      setFailure("No se ha podido conectar con la API. ¿Está arrancada con make api?");
    }
  }, []);

  const open = useCallback(async (id: string) => {
    const resp = await fetch(`/api/offers/${id}`);
    if (resp.ok) setSelected((await resp.json()) as OfferOut);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // Mientras el trabajo de extracción no termina, se vuelve a preguntar cada pocos segundos.
  useEffect(() => {
    if (selected?.status !== "pendiente") return;
    const timer = setTimeout(() => void open(selected.id).then(refresh), POLL_MS);
    return () => clearTimeout(timer);
  }, [selected, open, refresh]);

  function created(offer: OfferOut) {
    setSelected(offer);
    setPasteFor(null);
    void refresh();
  }

  return (
    <div className="offers">
      <div className="results">
        <PasteForm
          key={pasteFor ?? "nuevo"}
          initialUrl={pasteFor ?? ""}
          startWithText={pasteFor !== null}
          onCreated={created}
        />
        {failure && <p className="failure">{failure}</p>}
        {offers.length > 0 && (
          <fieldset>
            <legend>Tus anuncios</legend>
            <ul className="offer-list">
              {offers.map((o) => (
                <li key={o.id}>
                  <button
                    type="button"
                    aria-current={selected?.id === o.id ? "true" : undefined}
                    onClick={() => void open(o.id)}
                  >
                    <span className="offer-title">{o.title ?? o.url ?? "Texto pegado"}</span>
                    <span className="status">{STATUS[o.status]}</span>
                  </button>
                </li>
              ))}
            </ul>
          </fieldset>
        )}
        {auctions.length > 0 && <Auctions notices={auctions} onPaste={setPasteFor} />}
      </div>
      <section className="results" aria-live="polite">
        {selected ? (
          <OfferDetail key={`${selected.id}-${selected.status}`} offer={selected} onSaved={created} />
        ) : (
          <p className="empty">Pega un enlace o elige uno de tus anuncios.</p>
        )}
      </section>
    </div>
  );
}

function Auctions({
  notices,
  onPaste,
}: {
  notices: AuctionNotice[];
  onPaste: (url: string) => void;
}) {
  const [all, setAll] = useState(false);
  const shown = all ? notices : notices.slice(0, NOTICES_SHOWN);
  return (
    <fieldset>
      <legend>Subastas judiciales en Madrid</legend>
      <p className="hint">
        Avisos del BOE. Abre la subasta en el Portal, copia el texto del lote y pégalo aquí para
        analizarlo. {notices[0].attribution}.
      </p>
      <ul className="offer-list">
        {shown.map((n) => (
          <li key={n.portal_id} className="notice">
            <span className="offer-title">{n.court ?? n.title ?? n.portal_id}</span>
            <span className="status">
              {n.published_on ? formatDate(n.published_on) : ""} · {n.kind ?? "subasta judicial"}
            </span>
            <span className="notice-actions">
              {n.portal_url && (
                <a href={n.portal_url} target="_blank" rel="noopener noreferrer nofollow">
                  Abrir {n.portal_id}
                </a>
              )}
              {n.boe_url && (
                <a href={n.boe_url} target="_blank" rel="noopener noreferrer">
                  Aviso en el BOE
                </a>
              )}
              <button
                type="button"
                className="link-button"
                aria-label={`Pegar el texto de la subasta ${n.portal_id}`}
                onClick={() => onPaste(n.portal_url ?? "")}
              >
                Pegar su texto
              </button>
            </span>
          </li>
        ))}
      </ul>
      {!all && notices.length > NOTICES_SHOWN && (
        <button type="button" className="link-button" onClick={() => setAll(true)}>
          Ver las {notices.length}
        </button>
      )}
    </fieldset>
  );
}

const dateFormat = new Intl.DateTimeFormat("es-ES", { day: "numeric", month: "short" });

function formatDate(iso: string): string {
  return dateFormat.format(new Date(`${iso}T00:00:00`));
}

function PasteForm({
  onCreated,
  initialUrl = "",
  startWithText = false,
}: {
  onCreated: (offer: OfferOut) => void;
  initialUrl?: string;
  startWithText?: boolean;
}) {
  const [url, setUrl] = useState(initialUrl);
  const [text, setText] = useState("");
  const [pasteText, setPasteText] = useState(startWithText);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setMessage(null);
    const withText = pasteText && text.trim().length > 0;
    try {
      const resp = await fetch(withText ? "/api/offers/text" : "/api/offers/link", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(withText ? { text, url: url.trim() || null } : { url: url.trim() }),
      });
      const body = await resp.json();
      if (resp.ok) {
        setText("");
        setPasteText(false);
        onCreated(body as OfferOut);
      } else if (body.detail?.paste_text) {
        setPasteText(true);
        setMessage(body.detail.reason as string);
      } else {
        setMessage(
          typeof body.detail === "string" ? body.detail : "Revisa el enlace o el texto pegado.",
        );
      }
    } catch {
      setMessage("No se ha podido conectar con la API. ¿Está arrancada con make api?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate>
      <fieldset>
        <legend>Nuevo anuncio</legend>
        <div className="field">
          <label htmlFor="offer-url">Enlace del anuncio</label>
          <input
            id="offer-url"
            type="url"
            inputMode="url"
            placeholder="https://…"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        </div>
        {pasteText ? (
          <div className="field">
            <label htmlFor="offer-text">Texto del anuncio</label>
            <textarea
              id="offer-text"
              autoFocus={startWithText}
              value={text}
              onChange={(e) => setText(e.target.value)}
              aria-describedby="offer-text-help"
            />
            <small id="offer-text-help" className="hint">
              Selecciona todo el texto de la página del anuncio, cópialo y pégalo aquí.
            </small>
          </div>
        ) : (
          <button type="button" className="link-button" onClick={() => setPasteText(true)}>
            O pega el texto del anuncio
          </button>
        )}
        {message && <p className="failure">{message}</p>}
        <div className="actions">
          <button type="submit" disabled={loading || (!url.trim() && !text.trim())}>
            {loading ? "Leyendo…" : "Analizar"}
          </button>
        </div>
      </fieldset>
    </form>
  );
}

/** Confirmada: lo que el usuario dejó (también los campos que vació). Si no, lo propuesto. */
function initialValue(field: FieldOut, confirmed: boolean): string {
  return (confirmed ? field.confirmed : field.proposed) ?? "";
}

function OfferDetail({ offer, onSaved }: { offer: OfferOut; onSaved: (offer: OfferOut) => void }) {
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      offer.fields.map((f) => [f.name, initialValue(f, offer.status === "confirmada")]),
    ),
  );
  const [operation, setOperation] = useState(offer.operation ?? "desconocida");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function save(event: FormEvent) {
    event.preventDefault();
    const payload: Record<string, string | null> = {};
    const found: Record<string, string> = {};
    for (const field of offer.fields) {
      const raw = values[field.name]?.trim() ?? "";
      if (!raw) {
        payload[field.name] = null;
      } else if (field.kind === "number") {
        const clean = spanishNumber(raw);
        if (clean === null) found[field.name] = "Escribe solo el número";
        payload[field.name] = clean;
      } else {
        payload[field.name] = raw;
      }
    }
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    setSaving(true);
    setFailure(null);
    try {
      const resp = await fetch(`/api/offers/${offer.id}/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ operation, values: payload }),
      });
      const body = await resp.json();
      if (resp.ok) onSaved(body as OfferOut);
      else setFailure(typeof body.detail === "string" ? body.detail : "No se han podido guardar.");
    } catch {
      setFailure("No se ha podido conectar con la API.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <div className="offer-head">
        <h2>{offer.title ?? "Anuncio pegado"}</h2>
        {offer.url && (
          <a href={offer.url} target="_blank" rel="noopener noreferrer nofollow">
            {offer.url}
          </a>
        )}
      </div>
      {offer.status === "pendiente" ? (
        <p className="empty">
          Leyendo el anuncio. Puede tardar unos minutos; esta página se actualiza sola.
        </p>
      ) : (
        <p className="empty">
          {offer.status === "confirmada"
            ? offer.located
              ? `Datos confirmados. Ubicado en la sección censal ${offer.section_code ?? "—"}` +
                (offer.attribution ? ` (${offer.attribution}).` : ".")
              : "Datos confirmados. No se ha podido ubicar: revisa la dirección y el municipio."
            : "Revisa cada dato con la frase de la que sale. Corrige o completa lo que haga falta."}
        </p>
      )}
      <form onSubmit={save} noValidate>
        <fieldset>
          <legend>Datos del anuncio</legend>
          <div className="field">
            <label htmlFor="offer-operation">Operación</label>
            <select
              id="offer-operation"
              value={operation}
              onChange={(e) => setOperation(e.target.value)}
            >
              <option value="venta">Venta</option>
              <option value="alquiler">Alquiler</option>
              <option value="desconocida">No lo dice</option>
            </select>
          </div>
          <div className="confirm-grid">
            {offer.fields.map((field) => (
              <ConfirmField
                key={field.name}
                field={field}
                value={values[field.name] ?? ""}
                error={errors[field.name]}
                onChange={(value) => setValues({ ...values, [field.name]: value })}
              />
            ))}
          </div>
          {failure && <p className="failure">{failure}</p>}
          <div className="actions">
            <button type="submit" disabled={saving}>
              {saving ? "Guardando…" : "Confirmar datos"}
            </button>
          </div>
        </fieldset>
      </form>
      {offer.status === "confirmada" && offer.located && <Valuation offer={offer} />}
    </>
  );
}

/** Renta, precio y escenarios del inmueble, y lo pedido frente a lo estimado (F5.4). */
function Valuation({ offer }: { offer: OfferOut }) {
  const [valuation, setValuation] = useState<OfferValuation | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  useEffect(() => {
    let current = true;
    setValuation(null);
    setFailure(null);
    fetch(`/api/offers/${offer.id}/valuation`)
      .then(async (resp) => {
        const body = await resp.json();
        if (!current) return;
        if (resp.ok) setValuation(body as OfferValuation);
        else setFailure(typeof body.detail === "string" ? body.detail : "No se ha podido valorar.");
      })
      .catch(() => current && setFailure("No se ha podido conectar con la API."));
    return () => {
      current = false;
    };
  }, [offer]);

  if (failure) return <p className="failure">Sin valoración: {failure}</p>;
  if (!valuation) return <p className="empty">Valorando…</p>;
  const f = valuation.figures;
  return (
    <section className="valuation" aria-labelledby="valuation-title">
      <h2 id="valuation-title">Valoración</h2>
      {VALUATION_GROUPS.map((group) => {
        const keys = group.keys.filter((k) => f[k]);
        if (keys.length === 0) return null;
        return (
          <div key={group.title} className="group">
            <h3>{group.title}</h3>
            <div className="grid">
              {keys.map((k) => (
                <FigureView key={k} figure={f[k]} />
              ))}
            </div>
          </div>
        );
      })}
      <ul className="warnings">
        {valuation.notes.map((n) => (
          <li key={n}>{n}</li>
        ))}
      </ul>
      <p className="hint">Fuentes: {valuation.attribution.join(" · ")}.</p>
    </section>
  );
}

function ConfirmField({
  field,
  value,
  error,
  onChange,
}: {
  field: FieldOut;
  value: string;
  error?: string;
  onChange: (value: string) => void;
}) {
  const id = `c-${field.name}`;
  const label = LISTING_LABELS[field.name] ?? field.name;
  return (
    <div className="field">
      <label htmlFor={id}>
        {label}
        {field.origin && <span className="origin"> · {ORIGIN[field.origin]}</span>}
      </label>
      <input
        id={id}
        type="text"
        inputMode={field.kind === "number" ? "decimal" : undefined}
        value={value}
        aria-invalid={error ? true : undefined}
        aria-describedby={`${id}-help`}
        onChange={(e) => onChange(e.target.value)}
      />
      <div id={`${id}-help`}>
        {error && <small className="error">{error}</small>}
        {field.status === "verificado" && field.evidence && (
          <p className="quote">«{field.evidence}»</p>
        )}
        {field.status === "rechazado" && (
          <p className="quote rejected">Descartado: {field.reason}.</p>
        )}
        {field.status === "ausente" && <p className="quote">El anuncio no lo dice.</p>}
      </div>
    </div>
  );
}
