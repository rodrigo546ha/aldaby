"use client";

import { useState, type FormEvent } from "react";

import type { components } from "../lib/api-types";
import { amount, formatValue } from "../lib/format";
import { LineChart } from "./Charts";
import { FigureView } from "./FigureView";

type BidsOut = components["schemas"]["BidsOut"];
type ChargeRow = { concept: string; amount: string };

const EMPTY_CHARGE: ChargeRow = { concept: "", amount: "" };

// Simulador de puja (ADR-0047): la API rehace el plan a cada puja; la web solo lo muestra
export function Bids({ offerId, auction }: { offerId: string; auction: boolean }) {
  const [value, setValue] = useState("");
  const [charges, setCharges] = useState<ChargeRow[]>([EMPTY_CHARGE]);
  const [possession, setPossession] = useState("");
  const [cash, setCash] = useState(false);
  // Los lotes del BOE son subastas administrativas; las judiciales llegan como oferta pegada
  const [judicial, setJudicial] = useState(!auction);
  const [result, setResult] = useState<BidsOut | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function setCharge(index: number, row: ChargeRow) {
    setCharges((all) => all.map((c, i) => (i === index ? row : c)));
  }

  function removeCharge(index: number) {
    setCharges((all) => all.filter((_, i) => i !== index));
  }

  async function simulate(event: FormEvent) {
    event.preventDefault();
    setFailure(null);
    const parsed = [value, possession].map((t) => (t.trim() ? amount(t) : ""));
    const filled = charges.filter((c) => c.amount.trim());
    const chargeAmounts = filled.map((c) => amount(c.amount));
    if (parsed.some((p) => p === null) || chargeAmounts.some((p) => p === null)) {
      setFailure("Escribe los importes con cifras (por ejemplo, 150000 o 150000,50).");
      return;
    }
    const [auctionValue, possessionValue] = parsed;
    setBusy(true);
    try {
      const resp = await fetch(`/api/plans/offers/${offerId}/bids`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...(auctionValue ? { auction_value: auctionValue } : {}),
          charges: filled.map((c, i) => ({ concept: c.concept.trim(), amount: chargeAmounts[i] })),
          possession: possessionValue || "0",
          cash,
          judicial,
        }),
      });
      const body = await resp.json().catch(() => ({}));
      if (resp.ok) setResult(body as BidsOut);
      else if (Array.isArray(body.detail)) setFailure(body.detail.join(". "));
      else setFailure(typeof body.detail === "string" ? body.detail : "No se ha podido simular");
    } catch {
      setFailure("No se ha podido conectar con la API.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="plan-section" aria-labelledby="pujas">
      <h3 id="pujas">Simulador de puja</h3>
      <p className="hint">
        El valor de subasta es el precio de salida, no el final. Aquí ves tu plan a cada puja y la
        más alta con la que sigue cumpliendo lo que pides.
      </p>
      <form onSubmit={simulate}>
        <div className="field">
          <label htmlFor="bid-value">Valor de subasta (€)</label>
          <input
            id="bid-value"
            inputMode="decimal"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={auction ? "El del anuncio, si lo dejas vacío" : "150000"}
            required={!auction}
          />
        </div>
        <fieldset className="charges">
          <legend>Cargas que subsisten</legend>
          <p className="hint">
            Las que veas en la página de la subasta o en la certificación de cargas, una por fila: las
            paga quien se adjudica. Deja vacías las que se cancelan con la subasta.
          </p>
          {charges.map((c, i) => (
            <div className="charge-row" key={i}>
              <div className="field">
                <label htmlFor={`charge-concept-${i}`}>Carga</label>
                <input
                  id={`charge-concept-${i}`}
                  maxLength={200}
                  value={c.concept}
                  onChange={(e) => setCharge(i, { ...c, concept: e.target.value })}
                  placeholder="Hipoteca anterior, embargo, deuda de comunidad…"
                />
              </div>
              <div className="field">
                <label htmlFor={`charge-amount-${i}`}>Importe (€)</label>
                <input
                  id={`charge-amount-${i}`}
                  inputMode="decimal"
                  value={c.amount}
                  onChange={(e) => setCharge(i, { ...c, amount: e.target.value })}
                  placeholder="0"
                />
              </div>
              {charges.length > 1 && (
                <button type="button" className="link" onClick={() => removeCharge(i)}>
                  Quitar
                </button>
              )}
            </div>
          ))}
          <button
            type="button"
            className="link"
            onClick={() => setCharges((all) => [...all, EMPTY_CHARGE])}
            disabled={charges.length >= 30}
          >
            Añadir otra carga
          </button>
        </fieldset>
        <div className="field">
          <label htmlFor="bid-possession">Coste de recuperar la posesión (€)</label>
          <input
            id="bid-possession"
            inputMode="decimal"
            value={possession}
            onChange={(e) => setPossession(e.target.value)}
            placeholder="0"
          />
          <span className="hint">Si está ocupado: abogado, procurador y el tiempo sin cobrar.</span>
        </div>
        <label className="check">
          <input type="checkbox" checked={judicial} onChange={(e) => setJudicial(e.target.checked)} />
          Subasta judicial (depósito y fases de la Ley de Enjuiciamiento Civil)
        </label>
        <label className="check">
          <input type="checkbox" checked={cash} onChange={(e) => setCash(e.target.checked)} />
          Al contado, sin hipoteca
        </label>
        <button type="submit" disabled={busy}>
          {busy ? "Calculando cada puja…" : "Simular las pujas"}
        </button>
      </form>
      {failure && <p className="failure">{failure}</p>}
      {result && (
        <>
          <div className="grid">
            {result.max_bid ? (
              <FigureView figure={result.max_bid} title="Tu puja máxima" />
            ) : (
              <p className="failure">Ni con la puja más baja cumple tu plan.</p>
            )}
            <FigureView figure={result.auction_value} title="Valor de subasta" />
            {result.deposit && <FigureView figure={result.deposit} title="Depósito para pujar" />}
            {result.charges && <FigureView figure={result.charges} title="Cargas que asumes" />}
          </div>
          <LineChart
            title="Tu cash flow al mes a cada puja"
            series={["Cash flow tras impuestos", "Con la subida de tipos"]}
            points={[...result.levels]
              .sort((a, b) => Number(a.price.value) - Number(b.price.value))
              .map((l) => ({ x: l.price, ys: [l.cashflow, l.stressed ?? null], passes: l.passes }))}
            marker={result.max_bid ? { title: "Tu puja máxima", figure: result.max_bid } : null}
          />
          <table>
            <thead>
              <tr>
                <th scope="col">Puja</th>
                <th scope="col">Del valor</th>
                <th scope="col">Cash flow al mes</th>
                <th scope="col">Con subida de tipos</th>
                <th scope="col">TIR</th>
                <th scope="col">¿Cumple?</th>
              </tr>
            </thead>
            <tbody>
              {result.levels.map((lv) => (
                <tr key={lv.share}>
                  <td>{formatValue(lv.price.value, "EUR")}</td>
                  <td>{formatValue(lv.share, "ratio")}</td>
                  <td>{formatValue(lv.cashflow.value, "EUR")}</td>
                  <td>{lv.stressed ? formatValue(lv.stressed.value, "EUR") : "—"}</td>
                  <td>{lv.irr ? formatValue(lv.irr.value, "ratio") : "—"}</td>
                  <td title={lv.reasons.join(". ")}>{lv.passes ? "Sí" : "No"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {result.levels.some((lv) => lv.stage) && (
            <>
              <h4>Qué pasa con cada puja ante el juzgado</h4>
              <ul className="hint">
                {result.levels.map((lv) => (
                  <li key={lv.share}>
                    <strong>{formatValue(lv.share, "ratio")}</strong>: {lv.stage}
                  </li>
                ))}
              </ul>
            </>
          )}
          <ul className="warnings">
            {result.notes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
