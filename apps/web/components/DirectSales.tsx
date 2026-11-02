"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { components } from "../lib/api-types";
import { ANNOUNCEMENT_STATUS, formatValue, spanishNumber } from "../lib/format";
import { formatDate, LotCard } from "./Announcements";

type Sale = components["schemas"]["DirectSaleOut"];
type Detail = components["schemas"]["DirectSaleDetailOut"];

// Ventas directas del Patrimonio del Estado (ADR-0037): lotes de subastas desiertas a la venta por
// el tipo de salida hasta la fecha límite de la ficha.

export function DirectSales() {
  const [items, setItems] = useState<Sale[]>([]);
  const [selected, setSelected] = useState<Detail | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const pane = useRef<HTMLElement>(null);

  useEffect(() => {
    fetch("/api/patrimonio/sales")
      .then(async (resp) => {
        if (resp.ok) setItems((await resp.json()) as Sale[]);
        else setFailure("No se han podido cargar las ventas directas.");
      })
      .catch(() => setFailure("No se ha podido conectar con la API. ¿Está arrancada con make api?"));
  }, []);

  const open = useCallback(async (id: string) => {
    const resp = await fetch(`/api/patrimonio/sales/${id}`);
    if (!resp.ok) return;
    setSelected((await resp.json()) as Detail);
    if (window.matchMedia("(max-width: 860px)").matches) {
      requestAnimationFrame(() => pane.current?.scrollIntoView({ block: "start" }));
    }
  }, []);

  return (
    <div className="offers">
      <div className="results">
        {failure && <p className="failure">{failure}</p>}
        <fieldset>
          <legend>Ventas directas</legend>
          {items.length === 0 && !failure && <p className="empty">Aún no hay ventas directas.</p>}
          <ul className="offer-list stacked">
            {items.map((s) => {
              const price = s.price ? spanishNumber(s.price) : null;
              return (
                <li key={s.id}>
                  <button
                    type="button"
                    aria-current={selected?.id === s.id ? "true" : undefined}
                    onClick={() => void open(s.id)}
                  >
                    <span className="offer-title">{s.title ?? s.id}</span>
                    <span className="status">
                      {s.delegation && `${s.delegation} · `}
                      {price && `${formatValue(price, "EUR")} · `}
                      {s.deadline && `hasta el ${s.deadline} · `}
                      {ANNOUNCEMENT_STATUS[s.status]}
                      {s.lots > 0 && ` · ${s.lots} ${s.lots === 1 ? "lote" : "lotes"}`}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </fieldset>
      </div>
      <section ref={pane} className="results detail-pane" aria-live="polite">
        {selected ? (
          <SaleDetail detail={selected} />
        ) : (
          <p className="empty">Elige una venta para ver sus lotes y su texto.</p>
        )}
      </section>
    </div>
  );
}

function SaleDetail({ detail }: { detail: Detail }) {
  return (
    <>
      <div className="offer-head">
        <h2>{detail.title ?? detail.id}</h2>
        <p className="hint">
          {formatDate(detail.published_on)} ·{" "}
          {detail.url && (
            <a href={detail.url} target="_blank" rel="noopener noreferrer">
              Ver la ficha en Hacienda
            </a>
          )}
          {" · "}
          {detail.attribution}
        </p>
      </div>
      {detail.status === "pendiente" && (
        <p className="empty">Los lotes de esta venta aún no se han extraído.</p>
      )}
      {detail.lots.map((lot) => (
        <LotCard key={lot.id} lot={lot} />
      ))}
      <details>
        <summary>Texto de la ficha y de sus hojas de lote</summary>
        {detail.paragraphs.map((p, i) => (
          <p key={i} className="formula">
            {p}
          </p>
        ))}
      </details>
    </>
  );
}
