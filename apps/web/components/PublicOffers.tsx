"use client";

import { useState } from "react";

import { Announcements } from "./Announcements";
import { DirectSales } from "./DirectSales";

const TABS = [
  { id: "boe", label: "Anuncios del BOE" },
  { id: "patrimonio", label: "Ventas directas del Patrimonio" },
] as const;

type Tab = (typeof TABS)[number]["id"];

/** Oferta pública: anuncios del BOE (F4.4) y ventas directas del Patrimonio (ADR-0037). */
export function PublicOffers() {
  const [tab, setTab] = useState<Tab>("boe");
  return (
    <>
      <div className="tabs" role="tablist" aria-label="Fuente">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            id={`tab-${t.id}`}
            aria-selected={tab === t.id}
            aria-controls={`panel-${t.id}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
        {tab === "boe" ? <Announcements /> : <DirectSales />}
      </div>
    </>
  );
}
