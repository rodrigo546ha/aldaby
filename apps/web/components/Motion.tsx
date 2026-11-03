"use client";

import { useEffect, useState } from "react";

import { formatValue, label, type FigureOut } from "../lib/format";
import { Amount } from "./FigureView";

// Movimiento compartido (docs/PROPUESTA_UX.md, U1): esperas con forma y cifras que llegan.

/** Lo que se está calculando, con la forma que tendrá: filas de cifras o un bloque de texto. */
export function Skeleton({ label: text, shape = "figures" }: { label: string; shape?: "figures" | "text" }) {
  return (
    <div className={`skeleton skeleton-${shape}`} role="status">
      <span className="visually-hidden">{text}</span>
      {shape === "figures" ? (
        <>
          <div className="skeleton-row">
            <span /> <span /> <span />
          </div>
          <div className="skeleton-line" />
          <div className="skeleton-line short" />
          <div className="skeleton-line" />
        </>
      ) : (
        <>
          <div className="skeleton-line" />
          <div className="skeleton-line" />
          <div className="skeleton-line short" />
        </>
      )}
    </div>
  );
}

const COUNT_MS = 600;

/**
 * Una cifra del veredicto. Al aparecer cuenta desde cero hasta su valor, una sola vez; el valor que
 * queda es el de la API, formateado de su texto exacto. Con movimiento reducido no cuenta.
 */
export function VerdictFigure({ figure, title }: { figure: FigureOut; title?: string }) {
  const target = Number(figure.value);
  const [shown, setShown] = useState<number | null>(0);

  useEffect(() => {
    if (!Number.isFinite(target) || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setShown(null);
      return;
    }
    let frame = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / COUNT_MS);
      const eased = 1 - Math.pow(1 - t, 3);
      if (t < 1) {
        setShown(target * eased);
        frame = requestAnimationFrame(tick);
      } else {
        setShown(null);
      }
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target]);

  // Mientras cuenta se redondea a la precisión del valor final; al acabar, el texto exacto de la API
  const decimals = (figure.value.split(".")[1] ?? "").length;
  const text =
    shown === null ? formatValue(figure.value, figure.unit) : formatValue(shown.toFixed(decimals), figure.unit);
  return (
    <div className="verdict-figure">
      <span className="verdict-value" aria-hidden={shown !== null}>
        <Amount text={text} />
      </span>
      {shown !== null && <span className="visually-hidden">{formatValue(figure.value, figure.unit)}</span>}
      <span className="verdict-label">
        {title ?? label(figure.key)}
        {figure.provisional && <span className="prov-mark"> provisional</span>}
      </span>
    </div>
  );
}
