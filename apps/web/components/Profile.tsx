"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import type { components } from "../lib/api-types";
import { Callout } from "./Icon";
import { Skeleton } from "./Motion";
import { AppLink, DATA } from "./AppLink";
import { invalidatePlans } from "../lib/data";

type InterviewOut = components["schemas"]["InterviewOut"];
type DraftField = components["schemas"]["DraftFieldOut"];
type Region = components["schemas"]["RegionOut"];
type DocumentKind = components["schemas"]["DocumentIn"]["kind"];

// Entrevista de perfil (ADR-0020): las preguntas son fijas; de cada respuesta se sacan los datos
// con la frase de la que salen, y aquí se confirman o se corrigen antes de guardarlos cifrados.
const CHOICES: Record<string, [string, string][]> = {
  goal: [["renta", "Renta cada mes"], ["patrimonio", "Que gane valor"], ["mixto", "Las dos"]],
  risk_tolerance: [["baja", "Poco"], ["media", "Medio"], ["alta", "Mucho"]],
  management: [["activa", "La gestiono yo"], ["pasiva", "La delego"]],
};
const SOURCE: Record<string, string> = {
  respuesta: "De tu respuesta",
  calculado: "Calculado de tu respuesta",
  usuario: "Corregido por ti",
  documento: "De tu documento",
};
const KINDS: [DocumentKind, string][] = [
  ["nomina", "Nómina"],
  ["declaracion", "Declaración de la renta"],
  ["extracto", "Extracto bancario"],
];
const READ_BY: Record<string, string> = {
  texto: "texto pegado",
  pdf: "PDF",
  ocr: "escaneo (OCR)",
  "pdf+ocr": "PDF con páginas escaneadas (OCR)",
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
      if (resp.status !== 404)
        setFailure(
          typeof body.detail === "string"
            ? body.detail
            : resp.status >= 500
              ? "No se ha podido leer ahora. Vuelve a intentarlo en un momento: tu respuesta sigue escrita."
              : "Revisa lo que has escrito y vuelve a intentarlo.",
        );
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
    if (interview && interview.answers.length > 0 &&
        !window.confirm("¿Empezar de nuevo? Se borran tus respuestas y los datos sin confirmar.")) return;
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
      invalidatePlans(); // el plan de cada oferta sale ya con el perfil nuevo
      const refreshed = await call(`/api/profile/interviews/${interview.id}`);
      if (refreshed) setInterview(refreshed as InterviewOut);
    }
    setBusy(false);
  }

  if (!loaded) return <Skeleton label="Cargando tu perfil…" shape="text" />;

  if (!interview) {
    return (
      <section className="section-card profile-start" aria-labelledby="perfil-empezar">
        <h2 id="perfil-empezar">Tu perfil en una conversación</h2>
        <ol className="how-steps">
          <li>
            <strong>Contestas unas preguntas</strong> con tus palabras: ingresos, ahorro, deudas, edad y qué buscas.
          </li>
          <li>
            <strong>Ves cada dato con la frase de la que sale</strong> y lo corriges si no es así. Puedes añadir una nómina o
            tu declaración.
          </li>
          <li>
            <strong>Lo confirmas</strong> y con él se calcula tu plan en cada oferta.
          </li>
        </ol>
        <Callout tone="info">
          <p>Tus ingresos y deudas se guardan cifrados. Los documentos se leen y se descartan: solo queda lo que confirmes.</p>
        </Callout>
        {failure && (
          <Callout tone="danger">
            <p>{failure}</p>
          </Callout>
        )}
        <div className="actions">
          <button type="button" onClick={start} disabled={busy}>
            Empezar
          </button>
        </div>
      </section>
    );
  }

  const confirmed = interview.status === "confirmada";
  const required = interview.fields.filter((f) => f.required);
  const filled = (f: DraftField) => (f.field in edits ? edits[f.field].trim() !== "" : asText(f.value).trim() !== "");
  const done = required.filter(filled).length;
  return (
    <div className="profile">
      <section className="section-card interview" aria-labelledby="conversacion">
        <header className="interview-head">
          <h2 id="conversacion">Conversación</h2>
          {!confirmed && (
            <p className="interview-progress">
              {done === required.length ? "Tienes todos los datos obligatorios" : `${done} de ${required.length} datos obligatorios`}
            </p>
          )}
        </header>
        {!confirmed && (
          <div className="stepper-progress" aria-hidden="true">
            <span style={{ width: `${required.length ? (done / required.length) * 100 : 100}%` }} />
          </div>
        )}
        <ol className="transcript">
          {interview.answers.map((a, i) => (
            <li key={i}>
              <p className="asked">{a.question}</p>
              <p className="said">{a.text}</p>
            </li>
          ))}
        </ol>
        {interview.issues.length > 0 && (
          <Callout tone="warning">
            <ul className="plain-list">
              {interview.issues.map((issue) => (
                <li key={issue}>{issue}</li>
              ))}
            </ul>
          </Callout>
        )}
        {interview.next_question && !confirmed && (
          <form onSubmit={send} className="answer-form">
            <label htmlFor="answer" className="asked current">
              {interview.next_question.text}
            </label>
            <textarea
              id="answer"
              rows={3}
              value={text}
              placeholder="Escribe con tus palabras; puedes dar varios datos a la vez"
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) e.currentTarget.form?.requestSubmit();
              }}
              disabled={busy}
            />
            <div className="answer-actions">
              <span className="hint">Cmd o Ctrl + Intro para enviar</span>
              <button type="submit" disabled={busy || !text.trim()} aria-busy={busy}>
                {busy ? "Leyendo tu respuesta…" : "Responder"}
              </button>
            </div>
          </form>
        )}
        {!interview.next_question && !confirmed && (
          <Callout tone="success">
            <p>Ya está todo. Revisa los datos de tu perfil y confírmalos.</p>
          </Callout>
        )}
        {!confirmed && (
          <details className="more-fields">
            <summary>
              Añadir un documento <span className="more-fields-note">nómina, declaración o extracto</span>
            </summary>
            <DocumentUpload interview={interview} call={call} onDone={setInterview} />
          </details>
        )}
        {failure && (
          <Callout tone="danger">
            <p>{failure}</p>
          </Callout>
        )}
      </section>

      <section className="section-card draft" aria-labelledby="draft-title">
        <header>
          <h2 id="draft-title">Tu perfil</h2>
          <p>Cada dato dice de dónde sale. Corrígelo aquí si no es así.</p>
        </header>
        {confirmed && (
          <Callout tone="success">
            <p>
              <strong>Perfil confirmado y guardado cifrado.</strong> Ya se calcula tu plan en cada oferta.
            </p>
          </Callout>
        )}
        <div className="confirm-grid">
          {interview.fields.map((f) => (
            <FieldEditor
              key={f.field}
              field={f}
              regions={regions}
              value={f.field in edits ? edits[f.field] : asText(f.value)}
              edited={f.field in edits}
              missing={f.required && !filled(f)}
              disabled={confirmed || busy}
              onChange={(v) => setEdits((old) => ({ ...old, [f.field]: v }))}
            />
          ))}
        </div>
        <div className="draft-actions">
          {confirmed ? (
            <>
              <AppLink className="button-link primary" href="/mapa" data={DATA.map()}>
                Ver las ofertas que encajan
              </AppLink>
              <AppLink className="button-link" href="/busqueda">
                Ajustar tus supuestos
              </AppLink>
            </>
          ) : (
            <>
              <button type="button" onClick={confirm} disabled={busy || !interview.complete}>
                Confirmar perfil
              </button>
              {!interview.complete && (
                <span className="hint">
                  {required.length - done === 1 ? "Falta 1 dato obligatorio." : `Faltan ${required.length - done} datos obligatorios.`}
                </span>
              )}
            </>
          )}
          <button type="button" className="link-button draft-restart" onClick={start} disabled={busy}>
            Empezar de nuevo
          </button>
        </div>
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
  missing: boolean;
  disabled: boolean;
  onChange: (value: string) => void;
}) {
  const { field, regions, value, edited, missing, disabled, onChange } = props;
  const id = `profile-${field.field}`;
  const choices = CHOICES[field.field];
  return (
    <div className={`field draft-field${missing ? " is-missing" : ""}`}>
      <div className="draft-field-head">
        <label htmlFor={id}>
          {field.label}
          {!field.required && <span className="optional"> · opcional</span>}
        </label>
        {missing ? (
          <span className="tag danger">Falta</span>
        ) : (
          (edited || field.source) && (
            <span className={`tag ${edited ? "warning" : "info"}`}>{edited ? SOURCE.usuario : SOURCE[field.source!]}</span>
          )
        )}
      </div>
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
          placeholder={field.field === "descendant_birth_years" ? "Sin dato (p. ej. 2015, 2019)" : "Sin dato"}
        />
      )}
      {field.evidence && !edited && <p className="quote">«{field.evidence}»</p>}
      {field.note && !edited && <p className="quote">{field.note}</p>}
    </div>
  );
}

function DocumentUpload(props: {
  interview: InterviewOut;
  call: (url: string, init?: RequestInit) => Promise<unknown>;
  onDone: (interview: InterviewOut) => void;
}) {
  const { interview, call, onDone } = props;
  const [kind, setKind] = useState<DocumentKind>("nomina");
  const [file, setFile] = useState<File | null>(null);
  const [pasted, setPasted] = useState("");
  const [busy, setBusy] = useState(false);

  async function upload(event: FormEvent) {
    event.preventDefault();
    if (!file && !pasted.trim()) return;
    setBusy(true);
    // El documento viaja en base64 y la API lo lee en memoria: no se guarda (ADR-0021)
    const body = file
      ? { kind, content_base64: await toBase64(file) }
      : { kind, text: pasted };
    const updated = await call(`/api/profile/interviews/${interview.id}/documents`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (updated) {
      onDone(updated as InterviewOut);
      setFile(null);
      setPasted("");
    }
    setBusy(false);
  }

  return (
    <form onSubmit={upload} className="documents" aria-label="Añadir un documento">
      <p className="hint">
        Se lee y se descarta: solo guardamos los datos que confirmes, con la frase de la que salen.
        Los escaneos y las fotos se leen con OCR en este equipo.
      </p>
      <div className="field">
        <label htmlFor="document-kind">Documento</label>
        <select
          id="document-kind"
          value={kind}
          disabled={busy}
          onChange={(e) => setKind(e.target.value as DocumentKind)}
        >
          {KINDS.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="document-file">PDF, JPG o PNG (hasta 10 MB)</label>
        <input
          id="document-file"
          type="file"
          accept="application/pdf,image/jpeg,image/png"
          disabled={busy}
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
      </div>
      {!file && (
        <div className="field">
          <label htmlFor="document-text">O pega su texto</label>
          <textarea
            id="document-text"
            rows={3}
            value={pasted}
            disabled={busy}
            onChange={(e) => setPasted(e.target.value)}
          />
        </div>
      )}
      <div className="actions">
        <button type="submit" className="secondary" disabled={busy || (!file && !pasted.trim())}>
          {busy ? "Leyendo el documento…" : "Leer documento"}
        </button>
      </div>
      {interview.documents.length > 0 && (
        <ul className="hint">
          {interview.documents.map((d, i) => (
            <li key={i}>
              {KINDS.find(([k]) => k === d.kind)?.[1]} · {READ_BY[d.method] ?? d.method} ·{" "}
              {d.fields.length === 1 ? "1 dato" : `${d.fields.length} datos`}
              {d.truncated ? " · solo el principio" : ""}
            </li>
          ))}
        </ul>
      )}
    </form>
  );
}

function toBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1] ?? "");
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}
