"use client";

import { useState, type FormEvent } from "react";

import { amount } from "../lib/format";

// Lo que costaría reformar la oferta: la API lo suma a la compra y a lo que pones. La valoración
// es la de una vivienda en el estado habitual de la zona y no descuenta el estado.
export function Renovation({
  offerId,
  current,
  onSaved,
}: {
  offerId: string;
  current: string | null;
  onSaved: () => void;
}) {
  const [value, setValue] = useState(current ? current.replace(".", ",") : "");
  const [error, setError] = useState<string | null>(null);

  async function save(event: FormEvent) {
    event.preventDefault();
    const parsed = value.trim() ? amount(value) : null;
    if (value.trim() && parsed === null) {
      setError("Escribe un importe, por ejemplo 25000 o 25000,50");
      return;
    }
    const resp = await fetch(`/api/search/offers/${offerId}/renovation`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amount: parsed }),
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      setError(typeof body.detail === "string" ? body.detail : "No se ha podido guardar");
      return;
    }
    setError(null);
    onSaved();
  }

  return (
    <form className="rent-expectation" onSubmit={save}>
      <label htmlFor={`renovation-${offerId}`}>
        Lo que costaría reformarla, si hace falta (se suma a la compra y a lo que pones)
      </label>
      <input
        id={`renovation-${offerId}`}
        inputMode="decimal"
        value={value}
        placeholder="€; vacío = sin reforma"
        onChange={(e) => setValue(e.target.value)}
      />
      <button type="submit">Guardar</button>
      {error && <p className="failure">{error}</p>}
    </form>
  );
}
