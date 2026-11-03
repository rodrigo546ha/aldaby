import type { ReactNode } from "react";

import { formatValue, label, SOURCE_KIND, type FigureOut } from "../lib/format";

const PROVISIONAL_TITLE = "Depende de una norma sin verificar o de un supuesto por fijar";

/**
 * Una cifra con su fórmula, sus fuentes y el aviso PROVISIONAL (D11). En un bloque (`quiet`) la
 * fórmula y las fuentes van una vez para todo el bloque y el aviso es una marca pequeña.
 */
export function FigureView({ figure, title, quiet = false }: { figure: FigureOut; title?: string; quiet?: boolean }) {
  return (
    <div className="figure">
      <div className="figure-head">
        <span className="figure-label">{title ?? label(figure.key)}</span>
        {figure.provisional &&
          (quiet ? (
            <span className="prov-mark" title={PROVISIONAL_TITLE}>
              provisional
            </span>
          ) : (
            <span className="badge" title={PROVISIONAL_TITLE}>
              PROVISIONAL
            </span>
          ))}
      </div>
      <div className="figure-value">
        <Amount text={formatValue(figure.value, figure.unit)} />
      </div>
      <Range figure={figure} />
      {!quiet && (
        <details>
          <summary>Cómo se calcula</summary>
          <FigureSources figure={figure} />
        </details>
      )}
    </div>
  );
}

function Range({ figure }: { figure: FigureOut }) {
  if (figure.low === null || figure.high === null) return null;
  return (
    <div className="figure-range">
      entre {formatValue(figure.low, figure.unit)} y {formatValue(figure.high, figure.unit)}
    </div>
  );
}

function FigureSources({ figure }: { figure: FigureOut }) {
  return (
    <>
      <p className="formula">{figure.formula}</p>
      <ul className="sources">
        {figure.sources.map((s) => (
          <li key={`${s.kind}:${s.id}`}>
            <span className="source-kind">{SOURCE_KIND[s.kind] ?? s.kind}</span> {s.id}
            {s.provisional && <span className="source-provisional"> · provisional</span>}
          </li>
        ))}
      </ul>
    </>
  );
}

/**
 * Un tema del plan plegado: cerrado enseña su título y sus cifras clave; abierto, todas sus cifras y,
 * una sola vez, las fórmulas y fuentes del bloque. Lo provisional se resume en un recuento.
 */
export function FigureBlock({
  id,
  title,
  figures,
  keys = [],
  open = false,
  children,
}: {
  id: string;
  title: string;
  figures: FigureOut[];
  keys?: string[];
  open?: boolean;
  children?: ReactNode;
}) {
  const byKey = new Map(figures.map((f) => [f.key, f]));
  const summary = keys.map((k) => byKey.get(k)).filter((f): f is FigureOut => Boolean(f));
  const provisional = figures.filter((f) => f.provisional).length;
  return (
    <details className="block" open={open} id={`bloque-${id}`}>
      <summary className="block-head">
        <span className="block-title">{title}</span>
        <span className="block-keys">
          {summary.map((f) => (
            <span key={f.key} className="block-key">
              <span className="block-key-label">{label(f.key)}</span>
              <span className="block-key-value">
                <Amount text={formatValue(f.value, f.unit)} />
              </span>
            </span>
          ))}
        </span>
      </summary>
      <div className="block-body">
        {children}
        {figures.length > 0 && (
          <div className="grid">
            {figures.map((f) => (
              <FigureView key={f.key} figure={f} quiet />
            ))}
          </div>
        )}
        {figures.length > 0 && (
          <details className="block-sources">
            <summary>
              Fórmulas y fuentes
              {provisional > 0 && (
                <span className="prov-count">
                  {" "}· {provisional} de {figures.length} provisionales
                </span>
              )}
            </summary>
            <dl className="sources-list">
              {figures.map((f) => (
                <div key={f.key}>
                  <dt>{label(f.key)}</dt>
                  <dd>
                    <FigureSources figure={f} />
                  </dd>
                </div>
              ))}
            </dl>
          </details>
        )}
      </div>
    </details>
  );
}

/** El número no se parte nunca; la coletilla de la unidad («al mes», «años») va aparte y más pequeña. */
export function Amount({ text }: { text: string }) {
  const m = text.match(/^(.*?\d[\d.,]*(?:\s?[€%])?)\s([^\d€%\s].*)$/);
  if (!m) return <span className="figure-number">{text}</span>;
  return (
    <>
      <span className="figure-number">{m[1]}</span> <span className="figure-unit">{m[2]}</span>
    </>
  );
}

/** Un aviso; si enumera muchas reglas, la lista se pliega para que el aviso se lea de un vistazo. */
export function WarningItem({ text }: { text: string }) {
  const m = text.match(/^(.+?):\s(.+?)\.?$/);
  const ids = m ? m[2].split(", ") : [];
  if (!m || ids.length < 4) return <li>{text}</li>;
  return (
    <li>
      <details>
        <summary>
          {m[1]} {ids.length} reglas y parámetros
        </summary>
        <p className="warning-ids">{ids.join(", ")}.</p>
      </details>
    </li>
  );
}
