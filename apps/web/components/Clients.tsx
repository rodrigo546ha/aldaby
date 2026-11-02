"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import type { components } from "../lib/api-types";

type ClientOut = components["schemas"]["ClientOut"];

// Clientes del profesional (F7.2, ADR-0029): el activo lo guarda la API en una cookie.

async function fetchClients(): Promise<ClientOut[] | null> {
  const resp = await fetch("/api/clients");
  return resp.ok ? ((await resp.json()) as ClientOut[]) : null;
}

/** Selector del cliente activo en la barra: al cambiarlo, la página se recarga con él. */
export function ClientPicker() {
  const [clients, setClients] = useState<ClientOut[] | null>(null);

  useEffect(() => {
    if (window.location.pathname.startsWith("/acceso")) return;
    fetchClients().then(setClients).catch(() => undefined);
  }, []);

  async function choose(id: string) {
    if (id === "__nuevo") {
      window.location.assign("/clientes");
      return;
    }
    await fetch("/api/clients/active", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ client_id: id }),
    });
    window.location.reload();
  }

  if (clients === null) return null;
  const active = clients.find((c) => c.active);
  return (
    <label className="client-picker">
      <span>Cliente</span>
      <select value={active?.id ?? ""} onChange={(e) => choose(e.target.value)}>
        {!active && <option value="">{clients.length ? "Elige un cliente" : "Sin clientes"}</option>}
        {clients.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
        <option value="__nuevo">Gestionar clientes…</option>
      </select>
    </label>
  );
}

/** Alta y borrado de clientes. */
export function Clients() {
  const [clients, setClients] = useState<ClientOut[] | null>(null);
  const [name, setName] = useState("");
  const [informed, setInformed] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  const load = useCallback(async () => {
    const resp = await fetch("/api/clients");
    const body = await resp.json().catch(() => ({}));
    if (resp.ok) setClients(body as ClientOut[]);
    else setFailure(typeof body.detail === "string" ? body.detail : "No se han podido leer");
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function create(event: FormEvent) {
    event.preventDefault();
    setFailure(null);
    const resp = await fetch("/api/clients", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, informed }),
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      setFailure(typeof body.detail === "string" ? body.detail : "No se ha podido crear");
      return;
    }
    // El nuevo queda activo: a su perfil
    window.location.assign("/perfil");
  }

  async function remove(client: ClientOut) {
    const sure = window.confirm(
      `¿Borrar a «${client.name}» con su perfil y su entrevista? No se puede deshacer.`,
    );
    if (!sure) return;
    const resp = await fetch(`/api/clients/${client.id}`, { method: "DELETE" });
    if (!resp.ok) setFailure("No se ha podido borrar");
    await load();
  }

  async function choose(client: ClientOut) {
    await fetch("/api/clients/active", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ client_id: client.id }),
    });
    window.location.assign("/perfil");
  }

  return (
    <div className="clients">
      <form className="client-new" onSubmit={create}>
        <label htmlFor="client-name">Nuevo cliente</label>
        <input id="client-name" value={name} maxLength={80} placeholder="Nombre o alias"
               onChange={(e) => setName(e.target.value)} />
        <button type="submit" disabled={!informed}>Crear</button>
        <label className="check client-informed">
          <input type="checkbox" checked={informed} onChange={(e) => setInformed(e.target.checked)} />
          <span>
            He informado a mi cliente del tratamiento de sus datos (
            <a href="/legal/clausula-clientes" target="_blank" rel="noopener noreferrer">
              cláusula modelo
            </a>
            ).
          </span>
        </label>
      </form>
      <p className="hint">El nombre se guarda cifrado y solo lo ve tu organización.</p>
      {failure && <p className="failure" role="alert">{failure}</p>}
      {clients === null ? (
        !failure && <p className="empty">Cargando…</p>
      ) : clients.length === 0 ? (
        <p className="empty">Todavía no tienes clientes.</p>
      ) : (
        <ul className="client-list">
          {clients.map((c) => (
            <li key={c.id}>
              <strong>{c.name}</strong>
              <span className="origin">
                {c.active ? " · activo" : ""}
                {c.has_profile ? " · con perfil" : " · sin perfil"}
              </span>
              <span className="client-actions">
                {!c.active && (
                  <button type="button" className="link" onClick={() => choose(c)}>
                    Trabajar con este
                  </button>
                )}
                <button type="button" className="link" onClick={() => remove(c)}>
                  Borrar
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
