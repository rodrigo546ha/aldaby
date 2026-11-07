"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Swap } from "./Motion";

// Lista de espera y nivel gratuito de la página de presentación (F8.1, ADR-0041).

export function FreeTierLine() {
  const [plans, setPlans] = useState<number | null>(null);
  useEffect(() => {
    fetch("/api/waitlist/free-tier")
      .then(async (resp) => (resp.ok ? setPlans((await resp.json()).full_plans as number) : null))
      .catch(() => undefined);
  }, []);
  return (
    <p>
      Tu perfil, cuánto puedes comprar, la búsqueda de ofertas con tus cifras
      {plans !== null ? ` y el plan completo de ${plans} ofertas` : " y algunos planes completos"}, sin
      pagar nada.
    </p>
  );
}

export function Waitlist() {
  const [email, setEmail] = useState("");
  const [kind, setKind] = useState<"particular" | "profesional">("particular");
  const [consent, setConsent] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setFailure(null);
    try {
      const resp = await fetch("/api/waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, kind, consent }),
      });
      const body = await resp.json().catch(() => ({}));
      if (resp.ok) setMessage(body.message as string);
      else setFailure(typeof body.detail === "string" ? body.detail : "No se ha podido apuntar");
    } catch {
      setFailure("No se ha podido conectar. Inténtalo de nuevo en un rato.");
    }
    setBusy(false);
  }

  if (message) return <p className="waitlist-done" role="status">{message}</p>;
  return (
    <form className="waitlist-form" onSubmit={submit}>
      <div className="field">
        <label htmlFor="waitlist-email">Correo</label>
        <input id="waitlist-email" name="email" type="email" autoComplete="email" spellCheck={false}
               required value={email}
               onChange={(e) => setEmail(e.target.value)} />
      </div>
      <fieldset className="waitlist-kind">
        <legend>Soy</legend>
        <label className="check">
          <input type="radio" name="kind" checked={kind === "particular"}
                 onChange={() => setKind("particular")} />
          Particular: quiero invertir
        </label>
        <label className="check">
          <input type="radio" name="kind" checked={kind === "profesional"}
                 onChange={() => setKind("profesional")} />
          Profesional: asesor, intermediario o agencia
        </label>
      </fieldset>
      <label className="check consent">
        <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
        <span>
          Acepto la{" "}
          <a href="/legal/privacidad" target="_blank" rel="noopener noreferrer">política de privacidad</a>{" "}
          y que me escribáis a este correo para darme acceso.
        </span>
      </label>
      {failure && <p className="failure" role="alert">{failure}</p>}
      <button type="submit" disabled={!consent || busy}>
        <Swap>{busy ? "Apuntando…" : "Apuntarme"}</Swap>
      </button>
    </form>
  );
}
