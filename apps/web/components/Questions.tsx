"use client";

import { useEffect, useState, type FormEvent } from "react";

import type { components } from "../lib/api-types";
import { events, Segments, stageLabel, type Stage } from "./Advisor";
import { Points, pointsFrom } from "./Explain";

type AdvisorAnswerOut = components["schemas"]["AdvisorAnswerOut"];
type ConversationOut = components["schemas"]["ConversationOut"];

// Preguntas al asesor sobre el plan (ADR-0063). La API guarda la conversación cifrada y la borra a
// los días que diga (ADR-0064); el historial que ve el modelo lo pone ella. Cada respuesta llega
// entera y comprobada; sus cifras son Figures del plan.
const SUGGESTIONS = [
  "¿Y si la alquilo por habitaciones?",
  "¿Qué pasa si suben los tipos?",
  "¿Cómo es la zona?",
  "¿Está cara frente a lo que vale?",
];
type Turn = { question: string; answer: AdvisorAnswerOut | null; failure: string | null };

export function Questions({ offerId }: { offerId: string }) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [stages, setStages] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<string | null>(null);
  const [retention, setRetention] = useState<number | null>(null);

  // La conversación guardada de esta oferta, si la hay
  useEffect(() => {
    let alive = true;
    fetch(`/api/plans/offers/${offerId}/conversation`)
      .then((resp) => (resp.ok ? (resp.json() as Promise<ConversationOut>) : null))
      .then((saved) => {
        if (!alive || !saved) return;
        setRetention(saved.retention_days);
        setTurns(
          saved.turns.map((t) => ({
            question: t.question,
            answer: t.answer,
            failure: t.answer.answer ? null : "El asesor no pudo contestar con cifras comprobadas.",
          })),
        );
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [offerId]);

  async function forget() {
    const resp = await fetch(`/api/plans/offers/${offerId}/conversation`, { method: "DELETE" });
    if (resp.ok) setTurns([]);
  }

  async function ask(question: string) {
    const text = question.trim();
    if (text.length < 2 || busy) return;
    setBusy(true);
    setPending(text);
    setStages([]);
    setDraft("");
    const seen: Stage[] = [];
    let turn: Turn = { question: text, answer: null, failure: "El asesor no ha respondido" };
    try {
      const resp = await fetch(`/api/plans/offers/${offerId}/questions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text }),
      });
      if (!resp.ok || !resp.body) {
        const body = await resp.json().catch(() => ({}));
        turn = { ...turn, failure: typeof body.detail === "string" ? body.detail : "El asesor no ha respondido" };
      } else {
        for await (const event of events(resp)) {
          if (event.name === "etapa") {
            const stage = event.data as Stage;
            const label = stageLabel(stage, seen, "Escribe la respuesta");
            seen.push(stage);
            setStages((all) => (all[all.length - 1] === label ? all : [...all, label]));
          } else if (event.name === "resultado") {
            const answer = event.data as AdvisorAnswerOut;
            turn = {
              question: text,
              answer,
              failure: answer.answer ? null : "El asesor no ha podido contestar con cifras comprobadas. Prueba a preguntarlo de otra forma.",
            };
          } else if (event.name === "error") {
            turn = { ...turn, failure: (event.data as { detail?: string }).detail ?? "El asesor no ha podido terminar" };
          }
        }
      }
    } catch {
      turn = { ...turn, failure: "No se ha podido conectar con la API." };
    }
    setTurns((all) => [...all, turn]);
    setPending(null);
    setBusy(false);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void ask(draft);
  }

  return (
    <section className="plan-section questions" aria-labelledby="preguntas" aria-busy={busy}>
      <h3 id="preguntas">Pregunta al asesor</h3>
      {turns.map((t, i) => (
        <div key={i} className="qa">
          <p className="qa-question">{t.question}</p>
          {t.answer?.answer && (
            <p className="qa-answer">
              <Segments parts={t.answer.answer} />
            </p>
          )}
          {t.failure && <p className="failure">{t.failure}</p>}
          {t.answer && t.answer.notes.length > 0 && (
            // Los mismos avisos del plan, plegados: en cada respuesta se repetirían enteros
            <details className="advisor-extra">
              <summary>Avisos de estas cifras ({t.answer.notes.length})</summary>
              <Points items={pointsFrom(t.answer.notes, "info")} />
            </details>
          )}
        </div>
      ))}
      {pending && <p className="qa-question">{pending}</p>}
      {busy && (
        <ol className="advisor-stages" aria-live="polite">
          {stages.map((s, i) => (
            <li key={`${i}-${s}`} className={i === stages.length - 1 ? "current" : "done"}>
              {s}
            </li>
          ))}
        </ol>
      )}
      {turns.length === 0 && !busy && (
        <div className="chip-row">
          {SUGGESTIONS.map((s) => (
            <button key={s} type="button" className="chip" onClick={() => void ask(s)}>
              {s}
            </button>
          ))}
        </div>
      )}
      <form className="rent-expectation" onSubmit={submit}>
        <label htmlFor={`question-${offerId}`}>
          Tu pregunta sobre este plan. La conversación se guarda cifrada
          {retention ? ` ${retention} días desde la última pregunta` : ""} y puedes borrarla cuando
          quieras.
        </label>
        <input
          id={`question-${offerId}`}
          value={draft}
          maxLength={500}
          disabled={busy}
          placeholder="Por ejemplo: ¿me conviene más la hipoteca variable?"
          onChange={(e) => setDraft(e.target.value)}
        />
        <button type="submit" disabled={busy || draft.trim().length < 2}>
          Preguntar
        </button>
      </form>
      {turns.length > 0 && !busy && (
        <button type="button" className="link-button" onClick={() => void forget()}>
          Borrar la conversación
        </button>
      )}
    </section>
  );
}
