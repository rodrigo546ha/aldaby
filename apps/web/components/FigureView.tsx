import { formatValue, label, SOURCE_KIND, type FigureOut } from "../lib/format";

/** Una cifra con su fórmula, sus fuentes y el aviso PROVISIONAL (D11). */
export function FigureView({ figure, title }: { figure: FigureOut; title?: string }) {
  return (
    <div className="figure">
      <div className="figure-head">
        <span className="figure-label">{title ?? label(figure.key)}</span>
        {figure.provisional && (
          <span className="badge" title="Depende de una norma sin verificar o de un supuesto por fijar">
            PROVISIONAL
          </span>
        )}
      </div>
      <div className="figure-value"><Amount text={formatValue(figure.value, figure.unit)} /></div>
      {figure.low !== null && figure.high !== null && (
        <div className="figure-range">
          entre {formatValue(figure.low, figure.unit)} y {formatValue(figure.high, figure.unit)}
        </div>
      )}
      <details>
        <summary>Cómo se calcula</summary>
        <p className="formula">{figure.formula}</p>
        <ul className="sources">
          {figure.sources.map((s) => (
            <li key={`${s.kind}:${s.id}`}>
              <span className="source-kind">{SOURCE_KIND[s.kind] ?? s.kind}</span> {s.id}
              {s.provisional && <span className="source-provisional"> · provisional</span>}
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}

/** El número no se parte nunca; la coletilla de la unidad («al mes», «años») va aparte y más pequeña. */
function Amount({ text }: { text: string }) {
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
