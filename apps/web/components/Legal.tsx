"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";

import type { components } from "../lib/api-types";
import { formatDate } from "./Announcements";
import { Markdown } from "./Markdown";

type Summary = components["schemas"]["LegalSummaryOut"];
type LegalDocument = components["schemas"]["LegalDocumentOut"];

// Textos legales y su aceptación (F7.4, ADR-0039). Los textos vienen de la API, versionados.

export const FOOTER_LINKS = [
  { id: "aviso-legal", label: "Aviso legal" },
  { id: "condiciones", label: "Condiciones de uso" },
  { id: "privacidad", label: "Privacidad" },
  { id: "encargo", label: "Encargo del tratamiento" },
  { id: "cookies", label: "Cookies" },
] as const;

export function LegalFooter() {
  return (
    <footer className="legal-footer">
      <nav aria-label="Textos legales">
        {FOOTER_LINKS.map((l) => (
          <Link key={l.id} href={`/legal/${l.id}`}>
            {l.label}
          </Link>
        ))}
      </nav>
    </footer>
  );
}

export function LegalDocumentView({ id }: { id: string }) {
  const [doc, setDoc] = useState<LegalDocument | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  useEffect(() => {
    fetch(`/api/legal/${encodeURIComponent(id)}`)
      .then(async (resp) => {
        if (resp.ok) setDoc((await resp.json()) as LegalDocument);
        else setFailure(resp.status === 404 ? "Este documento no existe." : "No se ha podido cargar.");
      })
      .catch(() => setFailure("No se ha podido conectar con la API."));
  }, [id]);

  if (failure) return <p className="failure">{failure}</p>;
  if (!doc) return <p className="empty">Cargando…</p>;
  return (
    <article className="legal">
      <header className="intro">
        <h1>{doc.title}</h1>
        <p className="hint">
          Versión {doc.version} · en vigor desde el {formatDate(doc.effective_from)}
        </p>
      </header>
      {!doc.verified && (
        <p className="warnings">
          <strong>Borrador pendiente de revisión legal.</strong> Este texto aún no lo ha revisado un
          abogado
          {doc.missing.length > 0 && " y faltan datos del titular, marcados como «pendiente»"}.
        </p>
      )}
      <Markdown text={doc.text} />
    </article>
  );
}

/** Aceptar las versiones vigentes antes de seguir (cuenta nueva o texto cambiado). */
export function LegalAcceptance() {
  const params = useSearchParams();
  const [docs, setDocs] = useState<Summary[]>([]);
  const [pendingIds, setPendingIds] = useState<string[] | null>(null);
  const [agreed, setAgreed] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    Promise.all([fetch("/api/legal"), fetch("/api/auth/me")])
      .then(async ([list, me]) => {
        if (me.status === 401) {
          window.location.assign("/acceso");
          return;
        }
        setDocs((await list.json()) as Summary[]);
        setPendingIds(((await me.json()) as { pending_legal?: string[] }).pending_legal ?? []);
      })
      .catch(() => setFailure("No se ha podido conectar con la API."));
  }, []);

  function next(): string {
    const target = params.get("siguiente");
    return target && target.startsWith("/") && !target.startsWith("//") ? target : "/simulador";
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setFailure(null);
    const chosen = docs.filter((d) => pendingIds?.includes(d.id));
    const resp = await fetch("/api/legal/accept", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ documents: Object.fromEntries(chosen.map((d) => [d.id, d.version])) }),
    });
    const body = await resp.json().catch(() => ({}));
    setBusy(false);
    if (!resp.ok) {
      setFailure(typeof body.detail === "string" ? body.detail : "No se ha podido guardar");
      return;
    }
    if ((body.pending ?? []).length === 0) window.location.assign(next());
    else setPendingIds(body.pending);
  }

  if (pendingIds === null) return failure ? <p className="failure">{failure}</p> : <p className="empty">Cargando…</p>;
  if (pendingIds.length === 0) {
    return (
      <p>
        Ya has aceptado las versiones vigentes. <a href={next()}>Seguir</a>.
      </p>
    );
  }
  const toRead = docs.filter((d) => pendingIds.includes(d.id));
  return (
    <form className="access-form legal-accept" onSubmit={submit}>
      <p>Antes de seguir, lee y acepta:</p>
      <ul>
        {toRead.map((d) => (
          <li key={d.id}>
            <a href={`/legal/${d.id}`} target="_blank" rel="noopener noreferrer">
              {d.title}
            </a>{" "}
            <span className="hint">(versión {d.version})</span>
          </li>
        ))}
      </ul>
      <label className="check">
        <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} />
        He leído y acepto estos documentos.
      </label>
      {failure && <p className="failure" role="alert">{failure}</p>}
      <button type="submit" disabled={!agreed || busy}>
        {busy ? "Guardando…" : "Aceptar y seguir"}
      </button>
    </form>
  );
}
