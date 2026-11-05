"use client";

import { useState, type ReactNode } from "react";

import { label, type FigureOut } from "../lib/format";
import { humane, publisher, refKey, useSources, type FigureSource, type SourceInfo } from "../lib/sources";
import { Icon } from "./Icon";

// Explicaciones (DESIGN.md, «Explicaciones»): todo texto que explica algo en la ficha y en el plan
// sale de estas piezas, nunca como párrafo suelto. Entradilla, puntos con su tono, pasos, cambios,
// cita literal de la fuente, fórmula y fuentes. Ningún texto se reescribe: solo se ordena y se viste.

export type Tone = "info" | "warning" | "success" | "danger" | "neutral";

/** Una frase que presenta lo que viene: en gris, a la medida de lectura. */
export function Lede({ children }: { children: ReactNode }) {
  return <p className="lede">{children}</p>;
}

/** Rótulo pequeño dentro de una sección: «De dónde salen», «La compra»… */
export function ExplainHead({ children, as: Tag = "p" }: { children: ReactNode; as?: "p" | "h4" }) {
  return <Tag className="explain-head">{children}</Tag>;
}

/**
 * «Es una subasta: el precio final puede ser otro» → título «Es una subasta» y el resto como texto.
 * Solo si los dos puntos llegan pronto: una frase larga se queda entera.
 */
export function splitTitle(text: string): { title?: string; text: string } {
  const m = text.match(/^([^:«»()]{3,64}):\s+(.+)$/s);
  if (!m) return { text };
  const rest = m[2].trim();
  return { title: m[1].trim(), text: rest.charAt(0).toUpperCase() + rest.slice(1) };
}

export type Point = { key?: string; text: ReactNode; title?: ReactNode; tone?: Tone; href?: string | null };

/** Una lista de puntos en una sola tarjeta: cada punto con el icono de su tono. */
export function Points({ items, tone = "neutral", label: name }: { items: Point[]; tone?: Tone; label?: string }) {
  if (items.length === 0) return null;
  return (
    <ul className="points" aria-label={name}>
      {items.map((p, i) => {
        const t = p.tone ?? tone;
        return (
          <li key={p.key ?? i} className={`point ${t}`}>
            <span className="point-mark">
              <Icon name={t === "neutral" ? "dot" : t} small />
            </span>
            <div className="point-body">
              {p.title && <strong className="point-title">{p.title}</strong>}
              <span className="point-text">{p.text}</span>
              {p.href && <SourceLink href={p.href} />}
            </div>
          </li>
        );
      })}
    </ul>
  );
}

/** Los puntos desde frases sueltas de la API: cada una con su título si lo trae. */
export function pointsFrom(texts: string[], tone: Tone = "neutral"): Point[] {
  return texts.map((t) => ({ key: t, tone, ...splitTitle(t) }));
}

export type Step = { key: string; title: string; text: ReactNode; href?: string | null };

/** Pasos numerados: título, lo que hay que hacer y su fuente. */
export function Steps({ items }: { items: Step[] }) {
  return (
    <ol className="step-list">
      {items.map((s, i) => (
        <li key={s.key} className="step-row">
          <span className="step-n" aria-hidden="true">
            {i + 1}
          </span>
          <div className="step-body">
            <strong className="step-title">{s.title}</strong>
            <span className="step-text">{s.text}</span>
            {s.href && <SourceLink href={s.href} />}
          </div>
        </li>
      ))}
    </ol>
  );
}

/** Una cifra que cambia: lo que es hoy y lo que sería. */
export function Changes({ rows }: { rows: { key: string; label: string; before: string; after: string }[] }) {
  return (
    <ul className="changes-list">
      {rows.map((r) => (
        <li key={r.key}>
          <span className="change-label">{r.label}</span>
          <span className="change-values">
            <span className="change-before">{r.before}</span>
            <Icon name="arrow" small label="pasaría a" />
            <span className="change-after">{r.after}</span>
          </span>
        </li>
      ))}
    </ul>
  );
}

/** Lo que dice la fuente, tal cual: entre comillas, plegado si es largo. */
export function Quote({ text, cite }: { text: string; cite: ReactNode }) {
  const [open, setOpen] = useState(false);
  const long = text.length > 320;
  const letters = text.replace(/[^\p{L}]/gu, "");
  const caps = letters.length > 20 && letters === letters.toUpperCase();
  return (
    <figure className="cite-block">
      <blockquote className={[long && !open ? "clamped" : "", caps ? "caps" : ""].filter(Boolean).join(" ") || undefined}>
        {text}
      </blockquote>
      <figcaption>
        <span>{cite}</span>
        {long && (
          <button type="button" className="link-button" aria-expanded={open} onClick={() => setOpen(!open)}>
            {open ? "Ver menos" : "Leer entero"}
          </button>
        )}
      </figcaption>
    </figure>
  );
}

/** Enlace a la fuente oficial, diciendo de quién es. */
export function SourceLink({ href, children }: { href: string; children?: ReactNode }) {
  return (
    <a className="source-link" href={href} target="_blank" rel="noreferrer">
      {children ?? publisher(href)}
      <Icon name="external" small />
    </a>
  );
}

// ───────── Fórmulas y fuentes ─────────

const OPERATOR = /(\s[−×÷+=→·/]\s|\s-\s)/;

/** La fórmula de una cifra, con los operadores destacados y una línea por cláusula. */
export function Formula({ text }: { text: string }) {
  const clauses = text.split(/;\s+/).filter(Boolean);
  return (
    <div className="formula">
      {clauses.map((c, i) => (
        <span key={i} className="formula-line">
          {c.split(OPERATOR).map((part, j) =>
            j % 2 === 1 ? (
              <span key={j} className="op">
                {part.trim()}
              </span>
            ) : (
              part
            ),
          )}
        </span>
      ))}
    </div>
  );
}

const GROUPS: [string, string][] = [
  ["user_input", "Tus datos"],
  ["rule", "Normas"],
  ["param", "Parámetros"],
  ["dataset", "Datos públicos"],
  ["model", "Modelos"],
  ["assumption", "Supuestos"],
];
const SHOWN = 4;

type Numbered = { key: string; source: FigureSource; n: number };

/** Las fuentes, una vez cada una, agrupadas por lo que son y numeradas en ese orden. */
function numbered(sources: FigureSource[], info: Map<string, SourceInfo>): Numbered[] {
  const seen = new Map<string, FigureSource>();
  for (const s of sources) {
    const k = refKey(s);
    const prev = seen.get(k);
    if (!prev || (s.provisional && !prev.provisional)) seen.set(k, s);
  }
  const kindOf = (k: string, s: FigureSource) => info.get(k)?.kind ?? s.kind;
  const rank = (kind: string) => {
    const i = GROUPS.findIndex(([g]) => g === kind);
    return i < 0 ? GROUPS.length : i;
  };
  return [...seen.entries()]
    .map(([key, source], order) => ({ key, source, order }))
    .sort((a, b) => rank(kindOf(a.key, a.source)) - rank(kindOf(b.key, b.source)) || a.order - b.order)
    .map((x, i) => ({ key: x.key, source: x.source, n: i + 1 }));
}

/** Las fuentes agrupadas: «Tus datos», «Normas»… Cada grupo largo se pliega a sus cuatro primeras. */
export function SourceList({
  sources,
  numbers = false,
  compact = false,
}: {
  sources: FigureSource[];
  numbers?: boolean;
  compact?: boolean;
}) {
  const keys = sources.map(refKey);
  const info = useSources(keys);
  const list = numbered(sources, info);
  return <SourceGroups list={list} info={info} numbers={numbers} compact={compact} />;
}

function SourceGroups({
  list,
  info,
  numbers,
  compact = false,
}: {
  list: Numbered[];
  info: Map<string, SourceInfo>;
  numbers: boolean;
  compact?: boolean;
}) {
  const groups = new Map<string, Numbered[]>();
  for (const item of list) {
    const kind = info.get(item.key)?.kind ?? item.source.kind;
    groups.set(kind, [...(groups.get(kind) ?? []), item]);
  }
  return (
    <div className={compact ? "source-groups compact" : "source-groups"}>
      {[...groups.entries()].map(([kind, items]) => (
        <SourceGroup
          key={kind}
          title={GROUPS.find(([g]) => g === kind)?.[1] ?? "Otras"}
          items={items}
          info={info}
          numbers={numbers}
          compact={compact}
        />
      ))}
    </div>
  );
}

function SourceGroup({
  title,
  items,
  info,
  numbers,
  compact,
}: {
  title: string;
  items: Numbered[];
  info: Map<string, SourceInfo>;
  numbers: boolean;
  compact: boolean;
}) {
  const [all, setAll] = useState(false);
  const shown = all ? items : items.slice(0, compact ? 3 : SHOWN);
  const provisional = items.filter((i) => i.source.provisional).length;
  return (
    <div className="source-group">
      <p className="source-group-title">
        {title} <span className="source-count">{items.length}</span>
        {provisional > 0 && <span className="prov-mark">{provisional === items.length ? "provisionales" : `${provisional} provisionales`}</span>}
      </p>
      <ul className="source-items">
        {shown.map(({ key, source, n }) => {
          const s = info.get(key);
          return (
            <li key={key} className="source-item">
              {numbers && <span className="source-n">{n}</span>}
              <div className="source-body" title={compact ? s?.detail || undefined : undefined}>
                <span className="source-name">
                  {s?.name ?? humane(source.id)}
                  {source.provisional && provisional !== items.length && (
                    <span className="prov-dot" title="Provisional: norma sin verificar o supuesto por fijar">
                      <span className="visually-hidden"> (provisional)</span>
                    </span>
                  )}
                </span>
                {!compact && s?.detail && <span className="source-detail">{s.detail}</span>}
                {!compact && s?.url && <SourceLink href={s.url} />}
              </div>
            </li>
          );
        })}
      </ul>
      {items.length > (compact ? 3 : SHOWN) && (
        <button type="button" className="link-button source-more" aria-expanded={all} onClick={() => setAll(!all)}>
          {all ? "Ver menos" : `Ver las ${items.length}`}
        </button>
      )}
    </div>
  );
}

/** «1, 2, 3, 5, 7, 8» → «1–3, 5, 7–8». */
function ranges(ns: number[]): string {
  const sorted = [...new Set(ns)].sort((a, b) => a - b);
  const out: string[] = [];
  for (let i = 0; i < sorted.length; i++) {
    let j = i;
    while (j + 1 < sorted.length && sorted[j + 1] === sorted[j] + 1) j++;
    out.push(j > i ? `${sorted[i]}–${sorted[j]}` : String(sorted[i]));
    i = j;
  }
  return out.join(", ");
}

/** Cómo se calcula una cifra: su fórmula y sus fuentes agrupadas. */
export function HowCalculated({ figure }: { figure: FigureOut }) {
  return (
    <div className="how">
      <Formula text={figure.formula} />
      {figure.sources.length > 0 && <SourceList sources={figure.sources} compact />}
    </div>
  );
}

/**
 * Las fórmulas y fuentes de un tema del plan: cada cifra con su fórmula y los números de sus
 * fuentes; debajo, cada fuente una vez, como el anexo del PDF.
 */
export function BlockSources({ figures }: { figures: FigureOut[] }) {
  const all = figures.flatMap((f) => f.sources);
  const info = useSources(all.map(refKey));
  const list = numbered(all, info);
  const number = new Map(list.map((x) => [x.key, x.n]));
  return (
    <div className="how-block">
      <ul className="how-figures">
        {figures.map((f) => (
          <li key={f.key} className="how-figure">
            <span className="how-figure-label">{label(f.key)}</span>
            <Formula text={f.formula} />
            {f.sources.length > 0 && (
              <span className="how-refs">
                {f.sources.length === 1 ? "Fuente" : "Fuentes"} {ranges(f.sources.map((s) => number.get(refKey(s)) ?? 0))}
              </span>
            )}
          </li>
        ))}
      </ul>
      {list.length > 0 && (
        <>
          <ExplainHead>De dónde salen</ExplainHead>
          <SourceGroups list={list} info={info} numbers />
        </>
      )}
    </div>
  );
}

/** Notas y avisos de la API: el de las cifras provisionales, con los nombres de sus normas. */
export function notePoints(texts: string[], tone: Tone = "info"): Point[] {
  return texts.map((t) => provisionalPoint(t) ?? { key: t, tone, ...splitTitle(t) });
}

/**
 * Un aviso que enumera identificadores de normas y parámetros («Hay cifras PROVISIONALES porque
 * dependen de: a, b, c.»): se cuentan y se enseñan con sus nombres, no con sus identificadores.
 */
export function provisionalPoint(text: string): Point | null {
  const m = text.match(/^(.+?):\s(.+?)\.?$/s);
  if (!m) return null;
  const ids = m[2].split(/,\s*/).filter(Boolean);
  if (ids.length < 3 || !ids.every((id) => /^[a-z0-9][a-z0-9@._-]*$/.test(id))) return null;
  const provisional = /provisional/i.test(m[1]);
  return {
    key: text,
    tone: "warning",
    title: provisional ? "Hay cifras provisionales" : m[1],
    text: (
      <>
        {provisional
          ? `Dependen de ${ids.length} normas y parámetros que nadie ha verificado todavía en su fuente oficial, o de supuestos por fijar.`
          : `${ids.length} normas y parámetros.`}
        <details className="point-more">
          <summary>Cuáles son</summary>
          <SourceList sources={ids.map((id) => ({ kind: "", id, provisional: true }))} />
        </details>
      </>
    ),
  };
}
