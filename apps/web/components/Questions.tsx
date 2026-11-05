"use client";

import { useState, type FormEvent } from "react";

import type { components } from "../lib/api-types";
import { events, Segments, stageLabel, type Stage } from "./Advisor";
import { Points, pointsFrom } from "./Explain";

type AdvisorAnswerOut = components["schemas"]["AdvisorAnswerOut"];

// Preguntas al asesor sobre el plan (ADR-0063). La conversación vive solo en esta página: la API
// no la guarda. Cada respuesta llega entera y comprobada; sus cifras son Figures del plan.
const SUGGESTIONS = [
  "¿Y si la alquilo por habitaciones?",
  "¿Qué pasa si suben los tipos?",
  "¿Cómo es la zona?",
  "¿Está cara frente a lo que vale?",
];
const MAX_HISTORY = 6; // mensajes; la API no acepta más

type Turn = { question: string; answer: AdvisorAnswerOut | null; failure: string | null };

export function Questions({ offerId }: { offerId: string }) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [stages, setStages] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<string | null>(null);

  async function ask(question: string) {
    const text = question.trim();
    if (text.length < 2 || busy) return;
    // Solo las respuestas que pasaron la comprobación, con sus marcadores, y las últimas vueltas
    const history = turns
      .filter((t) => t.answer?.text)
      .flatMap((t) => [
        { role: "user" as const, content: t.question },
        { role: "assistant" as const, content: t.answer!.text! },
      ])
      .slice(-MAX_HISTORY);
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
        body: JSON.stringify({ question: text, history }),
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
          Tu pregunta sobre este plan. La conversación no se guarda: se pierde al salir de la página.
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
    </section>
  );
}
