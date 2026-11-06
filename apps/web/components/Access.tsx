"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import { Swap } from "./Motion";

// Acceso de la beta (F7.1, ADR-0028): la cookie de sesión la pone la API; aquí solo formularios.
const MIN_PASSWORD = 12;

export function Login() {
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const resp = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (resp.ok) {
        const next = params.get("siguiente");
        // Un particular empieza por su perfil; un profesional, por el simulador (ADR-0041)
        const home = (await resp.json()).role === "particular" ? "/perfil" : "/mapa";
        // Solo rutas propias: un enlace no puede llevar a otro sitio tras entrar
        window.location.assign(next && next.startsWith("/") && !next.startsWith("//") ? next : home);
        return;
      }
      const body = await resp.json().catch(() => ({}));
      setError(typeof body.detail === "string" ? body.detail : "No se ha podido entrar");
    } catch {
      setError("No se ha podido conectar con la API.");
    }
    setBusy(false);
  }

  return (
    <form className="access-form" onSubmit={submit}>
      <div className="field">
        <label htmlFor="email">Correo</label>
        <input id="email" type="email" autoComplete="username" required value={email}
               onChange={(e) => setEmail(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="password">Contraseña</label>
        <input id="password" type="password" autoComplete="current-password" required
               value={password} onChange={(e) => setPassword(e.target.value)} />
      </div>
      {error && <p className="failure" role="alert">{error}</p>}
      <button type="submit" disabled={busy}><Swap>{busy ? "Entrando…" : "Entrar"}</Swap></button>
      <p className="hint">¿Has olvidado la contraseña? Pide un enlace nuevo al equipo de Aldaby.</p>
    </form>
  );
}

export function ChoosePassword() {
  const params = useSearchParams();
  const token = params.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (password.length < MIN_PASSWORD) {
      setError(`La contraseña tiene que tener al menos ${MIN_PASSWORD} caracteres`);
      return;
    }
    if (password !== repeat) {
      setError("Las dos contraseñas no coinciden");
      return;
    }
    const resp = await fetch("/api/auth/password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, password }),
    });
    if (resp.ok) {
      setDone(true);
      return;
    }
    const body = await resp.json().catch(() => ({}));
    setError(typeof body.detail === "string" ? body.detail : "No se ha podido guardar");
  }

  if (!token) return <p className="failure">Falta el enlace: ábrelo tal como te llegó.</p>;
  if (done) {
    return (
      <p>
        Contraseña guardada. <a href="/acceso">Entra con tu correo</a>.
      </p>
    );
  }
  return (
    <form className="access-form" onSubmit={submit}>
      <div className="field">
        <label htmlFor="new-password">Contraseña nueva</label>
        <input id="new-password" type="password" autoComplete="new-password" required
               value={password} onChange={(e) => setPassword(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="repeat-password">Repítela</label>
        <input id="repeat-password" type="password" autoComplete="new-password" required
               value={repeat} onChange={(e) => setRepeat(e.target.value)} />
      </div>
      {error && <p className="failure" role="alert">{error}</p>}
      <button type="submit">Guardar contraseña</button>
    </form>
  );
}

/** Quién ha entrado y botón para salir; sin sesión vigente, a la página de acceso. */
export function Account() {
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    const path = window.location.pathname;
    if (path.startsWith("/acceso")) return;
    fetch("/api/auth/me")
      .then(async (resp) => {
        if (resp.ok) {
          const me = (await resp.json()) as { email: string; pending_legal?: string[] };
          setEmail(me.email);
          // Textos legales sin aceptar (ADR-0039): primero, aceptarlos; leerlos sí se puede.
          if ((me.pending_legal ?? []).length > 0 && !path.startsWith("/legal")) {
            window.location.assign(`/acceso/condiciones?siguiente=${encodeURIComponent(path)}`);
          }
        } else if (resp.status === 401 && !path.startsWith("/legal")) {
          window.location.assign("/acceso");
        }
      })
      .catch(() => undefined);
  }, []);

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" }).catch(() => undefined);
    window.location.assign("/acceso");
  }

  if (!email) return null;
  return (
    <span className="account">
      <span className="account-email">{email}</span>
      <button type="button" className="link" onClick={logout}>Salir</button>
    </span>
  );
}
