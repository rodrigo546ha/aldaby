"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { components } from "../lib/api-types";
import { ANNOUNCEMENT_STATUS, formatValue, LOT_LABELS, PROPERTY_TYPE } from "../lib/format";

type Announcement = components["schemas"]["AnnouncementOut"];
type Detail = components["schemas"]["AnnouncementDetailOut"];
type Lot = components["schemas"]["LotOut"];
type LotField = components["schemas"]["LotFieldOut"];

const MONEY = new Set(["price", "deposit"]);
const dateFormat = new Intl.DateTimeFormat("es-ES", { day: "numeric", month: "short", year: "numeric" });

function formatDate(iso: string | null | undefined): string {
  return iso ? dateFormat.format(new Date(`${iso}T00:00:00`)) : "";
}

export function Announcements() {
  const [items, setItems] = useState<Announcement[]>([]);
  const [selected, setSelected] = useState<Detail | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const pane = useRef<HTMLElement>(null);

  useEffect(() => {
    fetch("/api/boe/announcements")
      .then(async (resp) => {
        if (resp.ok) setItems((await resp.json()) as Announcement[]);
        else setFailure("No se han podido cargar los anuncios.");
      })
      .catch(() => setFailure("No se ha podido conectar con la API. ¿Está arrancada con make api?"));
  }, []);

  const open = useCallback(async (boeId: string) => {
    const resp = await fetch(`/api/boe/announcements/${boeId}`);
    if (!resp.ok) return;
    setSelected((await resp.json()) as Detail);
    // En pantallas estrechas el detalle va debajo de la lista: se lleva a la vista.
    if (window.matchMedia("(max-width: 860px)").matches) {
      requestAnimationFrame(() => pane.current?.scrollIntoView({ block: "start" }));
    }
  }, []);

  return (
    <div className="offers">
      <div className="results">
        {failure && <p className="failure">{failure}</p>}
        <fieldset>
          <legend>Anuncios</legend>
          {items.length === 0 && !failure && <p className="empty">Aún no hay anuncios.</p>}
          <ul className="offer-list stacked">
            {items.map((a) => (
              <li key={a.boe_id}>
                <button
                  type="button"
                  aria-current={selected?.boe_id === a.boe_id ? "true" : undefined}
                  onClick={() => void open(a.boe_id)}
                >
                  <span className="offer-title">{a.title ?? a.boe_id}</span>
                  <span className="status">
                    {formatDate(a.published_on)} · {ANNOUNCEMENT_STATUS[a.status]}
                    {a.lots > 0 && ` · ${a.lots} ${a.lots === 1 ? "lote" : "lotes"}`}
                    {a.corrections > 0 && " · corregido"}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </fieldset>
      </div>
      <section ref={pane} className="results detail-pane" aria-live="polite">
        {selected ? (
          <AnnouncementDetail detail={selected} onOpen={open} />
        ) : (
          <p className="empty">Elige un anuncio para ver sus lotes y su texto.</p>
        )}
      </section>
    </div>
  );
}

function AnnouncementDetail({ detail, onOpen }: { detail: Detail; onOpen: (id: string) => void }) {
  return (
    <>
      <div className="offer-head">
        <h2>{detail.title ?? detail.boe_id}</h2>
        <p className="hint">
          {detail.boe_id} · {formatDate(detail.published_on)} ·{" "}
          {detail.url && (
            <a href={detail.url} target="_blank" rel="noopener noreferrer">
              Ver en el BOE
            </a>
          )}
          {" · "}
          {detail.attribution}
        </p>
      </div>

      {detail.corrects && (
        <p className="warnings">
          Este anuncio corrige o cambia el{" "}
          <button type="button" className="link-button" onClick={() => onOpen(detail.corrects ?? "")}>
            {detail.corrects}
          </button>
          .
        </p>
      )}
      {detail.corrections.length > 0 && (
        <div className="warnings">
          <p>
            <strong>
              {detail.corrections.length === 1
                ? "Este anuncio tiene una corrección posterior."
                : `Este anuncio tiene ${detail.corrections.length} correcciones posteriores.`}
            </strong>{" "}
            Los lotes se extrajeron del anuncio original: revisa la corrección antes de usarlos.
          </p>
          {detail.corrections.map((c) => (
            <details key={c.boe_id}>
              <summary>
                {c.boe_id} · {formatDate(c.published_on)}
              </summary>
              {c.paragraphs.map((p, i) => (
                <p key={i} className="formula">
                  {p}
                </p>
              ))}
            </details>
          ))}
        </div>
      )}

      {detail.status === "pendiente" && (
        <p className="empty">Los lotes de este anuncio aún no se han extraído.</p>
      )}
      {detail.lots.map((lot) => (
        <LotCard key={lot.id} lot={lot} />
      ))}

      <details>
        <summary>Texto del anuncio</summary>
        {detail.paragraphs.map((p, i) => (
          <p key={i} className="formula">
            {p}
          </p>
        ))}
      </details>
    </>
  );
}

function LotCard({ lot }: { lot: Lot }) {
  const found = lot.fields.filter((f) => f.status === "verificado" && f.name !== "label");
  const rejected = lot.fields.filter((f) => f.status === "rechazado");
  return (
    <div className="figure">
      <div className="figure-head">
        <span className="figure-value small">
          {/* El título del lote es «Lote 1 · título del anuncio»: aquí basta la etiqueta. */}
          <strong>{lot.title?.split(" · ")[0] ?? "Lote"}</strong>
        </span>
        <span className="badge">SIN CONFIRMAR</span>
      </div>
      <p className="hint">
        {lot.property_type ? PROPERTY_TYPE[lot.property_type] ?? lot.property_type : "Tipo sin cita"}
        {" · "}
        {lot.located
          ? `Sección censal ${lot.section_code ?? "—"}` +
            (lot.location_attribution ? ` (${lot.location_attribution})` : "")
          : "Sin ubicar"}
      </p>
      <dl className="lot-fields">
        {found.map((f) => (
          <FieldRow key={f.name} field={f} />
        ))}
      </dl>
      {rejected.length > 0 && (
        <details>
          <summary>
            {rejected.length === 1 ? "1 dato descartado" : `${rejected.length} datos descartados`}
          </summary>
          <ul className="sources">
            {rejected.map((f) => (
              <li key={f.name}>
                {LOT_LABELS[f.name] ?? f.name}: {f.reason}
                {f.evidence && <> («{f.evidence}»)</>}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

function FieldRow({ field }: { field: LotField }) {
  const value = field.value ?? "";
  return (
    <>
      <dt>{LOT_LABELS[field.name] ?? field.name}</dt>
      <dd>
        <span className="figure-value small">{MONEY.has(field.name) ? formatValue(value, "EUR") : value}</span>
        {field.evidence && <span className="quote">«{field.evidence}»</span>}
      </dd>
    </>
  );
}
