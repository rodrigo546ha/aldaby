"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import type { components } from "../lib/api-types";

type InterviewOut = components["schemas"]["InterviewOut"];
type DraftField = components["schemas"]["DraftFieldOut"];
type Region = components["schemas"]["RegionOut"];

// Entrevista de perfil (ADR-0020): las preguntas son fijas; de cada respuesta se sacan los datos
// con la frase de la que salen, y aquí se confirman o se corrigen antes de guardarlos cifrados.
const CHOICES: Record<string, [string, string][]> = {
  goal: [["renta", "Renta cada mes"], ["patrimonio", "Que gane valor"], ["mixto", "Las dos"]],
  risk_tolerance: [["baja", "Poco"], ["media", "Medio"], ["alta", "Mucho"]],
  management: [["activa", "La gestiono yo"], ["pasiva", "La delego"]],
};
const SOURCE: Record<string, string> = {
  respuesta: "de tu respuesta",
  calculado: "calculado de tu respuesta",
  usuario: "corregido por ti",
};

type Edits = Record<string, string>;

export function Profile() {
  const [interview, setInterview] = useState<InterviewOut | null>(null);
  const [regions, setRegions] = useState<Region[]>([]);
  const [text, setText] = useState("");
  const [edits, setEdits] = useState<Edits>({});
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  const call = useCallback(async (url: string, init?: RequestInit) => {
    setFailure(null);
    try {
      const resp = await fetch(url, init);
      if (resp.ok) return resp.status === 204 ? null : await resp.json();
      const body = await resp.json().catch(() => ({}));
      if (resp.status !== 404) setFailure(typeof body.detail === "string" ? body.detail : "Error");
    } catch {
      setFailure("No se ha podido conectar con la API. ¿Está arrancada con make api?");
    }
    return undefined;
  }, []);

  useEffect(() => {
    (async () => {
      const current = await call("/api/profile/interviews/current");
      if (current) setInterview(current as InterviewOut);
      const listed = await call("/api/profile/regions");
      if (listed) setRegions(listed as Region[]);
      setLoaded(true);
    })();
  }, [call]);

  async function start() {
    setBusy(true);
    if (interview) await call(`/api/profile/interviews/${interview.id}`, { method: "DELETE" });
    const started = await call("/api/profile/interviews", { method: "POST" });
    setInterview((started as InterviewOut) ?? null);
    setEdits({});
    setBusy(false);
  }

  async function send(event: FormEvent) {
    event.preventDefault();
    if (!interview || !text.trim()) return;
    setBusy(true);
    const updated = await call(`/api/profile/interviews/${interview.id}/answers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (updated) {
      const next = updated as InterviewOut;
      // Lo que la nueva respuesta cambia pisa la corrección hecha a mano de ese campo
      setEdits((old) => {
        const kept = { ...old };
        for (const f of next.fields) {
          const before = interview.fields.find((g) => g.field === f.field);
          if (JSON.stringify(before?.value) !== JSON.stringify(f.value)) delete kept[f.field];
        }
        return kept;
      });
      setInterview(next);
      setText("");
    }
    setBusy(false);
  }

  async function confirm() {
    if (!interview) return;
    setBusy(true);
    const values: Record<string, unknown> = {};
    for (const f of interview.fields) {
      const raw = f.field in edits ? edits[f.field] : f.value;
      values[f.field] =
        f.field === "descendant_birth_years" && typeof raw === "string"
          ? raw.split(/[,\s]+/).filter(Boolean)
          : raw;
    }
    const done = await call(`/api/profile/interviews/${interview.id}/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ values }),
    });
    if (done) {
      const refreshed = await call(`/api/profile/interviews/${interview.id}`);
      if (refreshed) setInterview(refreshed as InterviewOut);
    }
    setBusy(false);
  }

  if (!loaded) return <p className="empty">Cargando…</p>;

  if (!interview) {
    return (
      <div className="profile-start">
        {failure && <p className="failure">{failure}</p>}
        <div className="actions">
          <button type="button" onClick={start} disabled={busy}>
            Empezar
          </button>
        </div>
      </div>
    );
  }

  const confirmed = interview.status === "confirmada";
  return (
    <div className="profile">
      <section className="interview" aria-label="Conversación">
        <ol className="transcript">
          {interview.answers.map((a, i) => (
            <li key={i}>
              <p className="asked">{a.question}</p>
              <p className="said">{a.text}</p>
            </li>
          ))}
        </ol>
        {interview.issues.length > 0 && (
          <ul className="warnings">
            {interview.issues.map((issue) => (
              <li key={issue}>{issue}</li>
            ))}
          </ul>
        )}
        {interview.next_question && !confirmed && (
          <form onSubmit={send} className="field">
            <label htmlFor="answer">{interview.next_question.text}</label>
            <textarea
              id="answer"
              rows={3}
              value={text}
              onChange={(e) => setText(e.target.value)}
              disabled={busy}
            />
            <div className="actions">
              <button type="submit" disabled={busy || !text.trim()}>
                {busy ? "Leyendo tu respuesta…" : "Responder"}
              </button>
            </div>
          </form>
        )}
        {!interview.next_question && !confirmed && (
          <p className="hint">Ya está todo: revisa los datos y confírmalos.</p>
        )}
        {failure && <p className="failure">{failure}</p>}
      </section>

      <section className="results" aria-labelledby="draft-title">
        <h2 id="draft-title">Tu perfil</h2>
        <div className="confirm-grid">
          {interview.fields.map((f) => (
            <FieldEditor
              key={f.field}
              field={f}
              regions={regions}
              value={f.field in edits ? edits[f.field] : asText(f.value)}
              edited={f.field in edits}
              disabled={confirmed || busy}
              onChange={(v) => setEdits((old) => ({ ...old, [f.field]: v }))}
            />
          ))}
        </div>
        <div className="actions">
          {confirmed ? (
            <p className="hint">Perfil confirmado y guardado cifrado.</p>
          ) : (
            <button type="button" onClick={confirm} disabled={busy || !interview.complete}>
              Confirmar perfil
            </button>
          )}
          <button type="button" className="secondary" onClick={start} disabled={busy}>
            Empezar de nuevo
          </button>
        </div>
        {!interview.complete && !confirmed && (
          <p className="hint">Para confirmar faltan los datos marcados como obligatorios.</p>
        )}
      </section>
    </div>
  );
}

function asText(value: DraftField["value"]): string {
  if (value == null) return "";
  return Array.isArray(value) ? value.join(", ") : value;
}

function FieldEditor(props: {
  field: DraftField;
  regions: Region[];
  value: string;
  edited: boolean;
  disabled: boolean;
  onChange: (value: string) => void;
}) {
  const { field, regions, value, edited, disabled, onChange } = props;
  const id = `profile-${field.field}`;
  const choices = CHOICES[field.field];
  return (
    <div className="field">
      <label htmlFor={id}>
        {field.label}
        {field.required && <span className="origin"> · obligatorio</span>}
        {(edited || field.source) && (
          <span className="origin"> · {edited ? SOURCE.usuario : SOURCE[field.source!]}</span>
        )}
      </label>
      {field.field === "residence" ? (
        <select id={id} value={value} disabled={disabled} onChange={(e) => onChange(e.target.value)}>
          <option value="">Sin dato</option>
          {regions.map((r) => (
            <option key={r.code} value={r.code}>
              {r.name}
            </option>
          ))}
        </select>
      ) : choices ? (
        <select id={id} value={value} disabled={disabled} onChange={(e) => onChange(e.target.value)}>
          <option value="">Sin dato</option>
          {choices.map(([v, label]) => (
            <option key={v} value={v}>
              {label}
            </option>
          ))}
        </select>
      ) : (
        <input
          id={id}
          inputMode={field.field === "descendant_birth_years" ? "text" : "decimal"}
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
          placeholder={field.field === "descendant_birth_years" ? "2015, 2019" : "Sin dato"}
        />
      )}
      {field.evidence && !edited && <p className="quote">«{field.evidence}»</p>}
      {field.note && !edited && <p className="quote">{field.note}</p>}
    </div>
  );
}
