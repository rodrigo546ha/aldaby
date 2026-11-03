"use client";

import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";

import { formatValue, type FigureOut } from "../lib/format";

// Gráficas del plan (ADR-0048): cada tramo, barra o punto lleva la cifra de la API como etiqueta; aquí
// solo se calculan posiciones y longitudes. Si falta una cifra, la gráfica no se dibuja.

const n = (f: FigureOut) => Number(f.value);
const text = (f: FigureOut) => formatValue(f.value, f.unit);

/** La gráfica se dibuja al entrar en pantalla (también al abrir el bloque que la contiene). */
function useReveal<T extends Element>() {
  const ref = useRef<T>(null);
  const [shown, setShown] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setShown(true);
        io.disconnect();
      }
    }, { threshold: 0.25 });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return [ref, shown] as const;
}

function Chart({ title, summary, children }: { title: string; summary: string; children: ReactNode }) {
  const [ref, shown] = useReveal<HTMLElement>();
  return (
    <figure ref={ref} className={shown ? "chart is-in" : "chart"}>
      <figcaption className="chart-title">{title}</figcaption>
      <div role="img" aria-label={summary}>
        {children}
      </div>
    </figure>
  );
}

const delay = (i: number) => ({ "--i": i }) as CSSProperties;

export type Segment = { title: string; figure: FigureOut };

/** Barras apiladas a la misma escala: cada fila suma sus tramos y se compara con las demás. */
export function StackedRows({
  title,
  rows,
}: {
  title: string;
  rows: { label: string; segments: Segment[] }[];
}) {
  const full = rows.filter((r) => r.segments.length > 0);
  if (full.length === 0) return null;
  const scale = Math.max(...full.map((r) => r.segments.reduce((s, x) => s + Math.max(0, n(x.figure)), 0)));
  if (!(scale > 0)) return null;
  const summary = full
    .map((r) => `${r.label}: ${r.segments.map((s) => `${s.title} ${text(s.figure)}`).join(", ")}`)
    .join(". ");
  let i = 0;
  return (
    <Chart title={title} summary={summary}>
      <div className="stacked">
        {full.map((r) => (
          <div key={r.label} className="stacked-row">
            <span className="chart-row-label">{r.label}</span>
            <div className="stacked-bar">
              {r.segments.map((s, k) => (
                <span
                  key={s.title}
                  className={`bar tone-${k + 1}`}
                  style={{ width: `${(Math.max(0, n(s.figure)) / scale) * 100}%`, ...delay(i++) }}
                />
              ))}
            </div>
            <div className="chart-legend">
              {r.segments.map((s, k) => (
                <span key={s.title} className="legend-item">
                  <span className={`swatch tone-${k + 1}`} aria-hidden="true" />
                  {s.title} <strong>{text(s.figure)}</strong>
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Chart>
  );
}

/** Barras a un lado y otro del cero: el mismo importe en varios escenarios. */
export function DivergingBars({ title, items }: { title: string; items: { title: string; note?: string; figure: FigureOut }[] }) {
  if (items.length < 2) return null;
  const scale = Math.max(...items.map((x) => Math.abs(n(x.figure))));
  if (!(scale > 0)) return null;
  const hasNeg = items.some((x) => n(x.figure) < 0);
  const hasPos = items.some((x) => n(x.figure) > 0);
  // El cero va donde lo pidan los datos: a la derecha si todo es negativo, en medio si hay de los dos
  const zero = hasNeg && hasPos ? 50 : hasNeg ? 100 : 0;
  const span = hasNeg && hasPos ? 50 : 100;
  const summary = items.map((x) => `${x.title}: ${text(x.figure)}`).join(". ");
  return (
    <Chart title={title} summary={summary}>
      <div className="diverging" style={{ "--zero": `${zero}%` } as CSSProperties}>
        {items.map((x, i) => {
          const v = n(x.figure);
          const w = (Math.abs(v) / scale) * span;
          return (
            <div key={x.title} className="diverging-row">
              <span className="chart-row-label">
                {x.title}
                {x.note && <span className="chart-note">{x.note}</span>}
              </span>
              <div className="diverging-track">
                <span
                  className={`bar ${v < 0 ? "neg" : "pos"}`}
                  style={{ width: `${w}%`, [v < 0 ? "right" : "left"]: `${v < 0 ? 100 - zero : zero}%`, ...delay(i) }}
                />
              </div>
              <span className={`chart-value ${v < 0 ? "neg" : ""}`}>{text(x.figure)}</span>
            </div>
          );
        })}
      </div>
    </Chart>
  );
}

/** Dos opciones frente a frente en cada concepto; cada par con su propia escala. */
export function PairedBars({
  title,
  names,
  groups,
}: {
  title: string;
  names: [string, string];
  groups: { title: string; a: FigureOut; b: FigureOut }[];
}) {
  if (groups.length === 0) return null;
  const summary = groups
    .map((g) => `${g.title}: ${names[0]} ${text(g.a)}, ${names[1]} ${text(g.b)}`)
    .join(". ");
  let i = 0;
  return (
    <Chart title={title} summary={summary}>
      <div className="paired">
        {groups.map((g) => {
          const scale = Math.max(n(g.a), n(g.b));
          return (
            <div key={g.title} className="paired-group">
              <span className="chart-row-label">{g.title}</span>
              {([g.a, g.b] as const).map((f, k) => (
                <div key={names[k]} className="paired-row">
                  <span className="paired-name">{names[k]}</span>
                  <div className="paired-track">
                    <span
                      className={`bar tone-${k + 1}`}
                      style={{ width: `${scale > 0 ? (n(f) / scale) * 100 : 0}%`, ...delay(i++) }}
                    />
                  </div>
                  <span className="chart-value">{text(f)}</span>
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </Chart>
  );
}

/** Escenarios sobre una franja con el cero marcado: dónde cae cada uno, no cuánto suma. */
export function ScenarioStrip({ title, items }: { title: string; items: { title: string; figure: FigureOut; main?: boolean }[] }) {
  if (items.length < 2) return null;
  const values = items.map((x) => n(x.figure));
  const lo = Math.min(0, ...values);
  const hi = Math.max(0, ...values);
  if (!(hi > lo)) return null;
  const pos = (v: number) => ((v - lo) / (hi - lo)) * 100;
  const summary = items.map((x) => `${x.title}: ${text(x.figure)}`).join(". ");
  return (
    <Chart title={title} summary={summary}>
      <div className="strip">
        <div className="strip-track">
          <span className="strip-range" style={{ left: `${pos(Math.min(...values))}%`, width: `${pos(Math.max(...values)) - pos(Math.min(...values))}%` }} />
          <span className="strip-zero" style={{ left: `${pos(0)}%` }} aria-hidden="true">
            <span className="strip-zero-label">{formatValue("0", items[0].figure.unit)}</span>
          </span>
          {items.map((x, i) => (
            <span
              key={x.title}
              className={x.main ? "strip-dot main" : "strip-dot"}
              style={{ left: `${pos(n(x.figure))}%`, ...delay(i) }}
            />
          ))}
        </div>
        <div className="strip-labels">
          {items.map((x) => (
            <span key={x.title} className={x.main ? "strip-label main" : "strip-label"}>
              <span className="chart-note">{x.title}</span>
              <strong>{text(x.figure)}</strong>
            </span>
          ))}
        </div>
      </div>
    </Chart>
  );
}

export type LinePoint = { x: FigureOut; ys: (FigureOut | null)[]; passes: boolean };

/**
 * Líneas sobre un eje x de cifras (la puja). Los puntos que cumplen el plan van llenos y los que no,
 * huecos; la marca vertical señala un valor de x de la API (la puja máxima).
 */
export function LineChart({
  title,
  series,
  points,
  marker,
}: {
  title: string;
  series: string[];
  points: LinePoint[];
  marker?: { title: string; figure: FigureOut } | null;
}) {
  if (points.length < 2) return null;
  const xs = points.map((p) => n(p.x));
  const ys = points.flatMap((p) => p.ys.filter((y): y is FigureOut => Boolean(y)).map(n));
  const unit = points.find((p) => p.ys[0])?.ys[0]?.unit ?? "";
  const x0 = Math.min(...xs);
  const x1 = Math.max(...xs);
  const y0 = Math.min(0, ...ys);
  const y1 = Math.max(0, ...ys);
  if (!(x1 > x0) || !(y1 > y0)) return null;
  // Posiciones en % del área: la línea se estira con el ancho y los puntos siguen redondos (van en HTML)
  const px = (v: number) => 2 + ((v - x0) / (x1 - x0)) * 96;
  const py = (v: number) => 6 + (1 - (v - y0) / (y1 - y0)) * 88;
  const first = points[0];
  const last = points[points.length - 1];
  const summary =
    `${series.map((s, k) => `${s}: de ${first.ys[k] ? text(first.ys[k]!) : "sin dato"} con ${text(first.x)} a ` +
      `${last.ys[k] ? text(last.ys[k]!) : "sin dato"} con ${text(last.x)}`).join(". ")}` +
    (marker ? `. ${marker.title}: ${text(marker.figure)}` : "");
  const m = marker && n(marker.figure) >= x0 && n(marker.figure) <= x1 ? px(n(marker.figure)) : null;
  return (
    <Chart title={title} summary={summary}>
      <div className="line-area">
        <svg className="line-chart" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <line className="axis-zero" x1={0} x2={100} y1={py(0)} y2={py(0)} vectorEffect="non-scaling-stroke" />
          {m !== null && (
            <line className="axis-marker" x1={m} x2={m} y1={0} y2={100} vectorEffect="non-scaling-stroke" />
          )}
          {series.map((s, k) => {
            const pts = points.filter((p) => p.ys[k]);
            const d = pts.map((p, j) => `${j ? "L" : "M"}${px(n(p.x)).toFixed(2)},${py(n(p.ys[k]!)).toFixed(2)}`).join(" ");
            return <path key={s} d={d} className={`line tone-${k + 1}`} vectorEffect="non-scaling-stroke" />;
          })}
        </svg>
        <span className="axis-zero-label" style={{ top: `${py(0)}%` }}>
          {formatValue("0", unit)}
        </span>
        {series.map((s, k) =>
          points
            .filter((p) => p.ys[k])
            .map((p) => (
              <span
                key={`${s}-${p.x.value}`}
                className={`line-dot tone-${k + 1}${p.passes ? " pass" : ""}`}
                style={{ left: `${px(n(p.x))}%`, top: `${py(n(p.ys[k]!))}%` }}
              />
            )),
        )}
      </div>
      <div className="line-axis">
        <span>{text(first.x)}</span>
        {marker && (
          <span className="line-marker-label">
            {marker.title} <strong>{text(marker.figure)}</strong>
          </span>
        )}
        <span>{text(last.x)}</span>
      </div>
      <div className="chart-legend">
        {series.map((s, k) => (
          <span key={s} className="legend-item">
            <span className={`swatch line tone-${k + 1}`} aria-hidden="true" />
            {s}
          </span>
        ))}
        <span className="legend-item">
          <span className="swatch dot-pass" aria-hidden="true" /> cumple tu plan
        </span>
        <span className="legend-item">
          <span className="swatch dot-fail" aria-hidden="true" /> no lo cumple
        </span>
      </div>
    </Chart>
  );
}

/** Las gráficas de un tema del plan o del simulador, con las cifras que haya de ese tema. */
export function TopicCharts({ topic, figures }: { topic: string; figures: Map<string, FigureOut> }) {
  const get = (k: string) => figures.get(k);
  const seg = (title: string, k: string): Segment[] => {
    const f = get(k);
    return f ? [{ title, figure: f }] : [];
  };
  if (topic === "compra") {
    if (!get("offer.price")) return null;
    return (
      <StackedRows
        title="Lo que cuesta comprarla y cómo se paga"
        rows={[
          {
            label: "Lo que cuesta",
            segments: [
              ...seg("Precio", "offer.price"),
              ...seg("Gastos que fija la normativa", "purchase_costs.regulated"),
              ...seg("Gestoría, tasación y copias", "purchase_costs.other"),
            ],
          },
          {
            label: "Cómo se paga",
            segments: [...seg("Tu dinero", "cashflow.cash_invested"), ...seg("Préstamo", "financing.loan")],
          },
        ]}
      />
    );
  }
  if (topic === "estres") {
    const shock = get("assumption.rate_shock");
    const items = [
      { title: "Hoy", key: "cashflow.monthly_after_tax" },
      { title: "Con la renta baja de la zona", key: "plan.low_rent_cashflow" },
      {
        title: "Con la subida de tipos",
        key: "term.stressed_monthly_cashflow",
        note: shock ? `+${formatValue(shock.value, shock.unit)} al plazo recomendado` : "al plazo recomendado",
      },
    ].flatMap((x) => {
      const f = get(x.key);
      return f ? [{ title: x.title, note: x.note, figure: f }] : [];
    });
    return <DivergingBars title="Tu cash flow al mes, tras impuestos" items={items} />;
  }
  if (topic === "hipoteca") {
    const pair = (title: string, metric: string) => {
      const a = get(`mortgage_comparison.fija.${metric}`);
      const b = get(`mortgage_comparison.variable.${metric}`);
      return a && b ? [{ title, a, b }] : [];
    };
    return (
      <PairedBars
        title="Hipoteca fija frente a variable"
        names={["Fija", "Variable"]}
        groups={[
          ...pair("Primera cuota", "first_payment"),
          ...pair("Cuota más alta con la subida de tipos", "stressed_max_payment"),
          ...pair("Intereses en toda la hipoteca", "expected_total_interest"),
        ]}
      />
    );
  }
  if (topic === "venta") {
    const items = [
      { title: "Conservador", key: "irr.rate_conservative" },
      { title: "Base", key: "irr.rate", main: true },
      { title: "Optimista", key: "irr.rate_optimistic" },
    ].flatMap((x) => {
      const f = get(x.key);
      return f ? [{ title: x.title, figure: f, main: x.main }] : [];
    });
    return <ScenarioStrip title="Rentabilidad anual (TIR) según cómo evolucione el precio" items={items} />;
  }
  return null;
}
