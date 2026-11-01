"use client";

import { useEffect, useState, type ChangeEvent, type CSSProperties, type FormEvent } from "react";

import type { components } from "../lib/api-types";

type BrandingOut = components["schemas"]["BrandingOut"];

// Marca del profesional en sus planes (F7.3, ADR-0030): la API comprueba el color y reescribe el
// logotipo; aquí solo el formulario y la vista previa.

export function useBranding(): [BrandingOut | null, number, (b: BrandingOut) => void] {
  const [brand, setBrand] = useState<BrandingOut | null>(null);
  const [version, setVersion] = useState(0);
  useEffect(() => {
    fetch("/api/branding")
      .then(async (resp) => (resp.ok ? setBrand((await resp.json()) as BrandingOut) : null))
      .catch(() => undefined);
  }, []);
  return [brand, version, (b) => {
    setBrand(b);
    setVersion((v) => v + 1);
  }];
}

/** La cabecera con la marca, como sale en el PDF. */
export function BrandHeader({ brand, version }: { brand: BrandingOut | null; version: number }) {
  if (!brand || !(brand.display_name || brand.contact || brand.intro || brand.has_logo)) {
    return null;
  }
  const accent = brand.color ? ({ borderColor: brand.color } as CSSProperties) : undefined;
  return (
    <section className="brand-header" style={accent}>
      <div className="brand-line">
        {brand.has_logo && (
          // eslint-disable-next-line @next/next/no-img-element
          <img className="brand-logo" src={`/api/branding/logo?v=${version}`} alt="" />
        )}
        <div>
          {brand.display_name && (
            // El color va solo en la línea: sobre el fondo oscuro de la web el texto no se leería
            <p className="brand-name">{brand.display_name}</p>
          )}
          {brand.contact && <p className="hint">{brand.contact}</p>}
        </div>
      </div>
      {brand.intro?.split("\n\n").map((p) => (
        <p key={p}>{p}</p>
      ))}
    </section>
  );
}

export function BrandingEditor() {
  const [brand, version, setBrand] = useBranding();
  const [form, setForm] = useState({ display_name: "", contact: "", color: "", intro: "" });
  const [failure, setFailure] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!brand) return;
    setForm({
      display_name: brand.display_name ?? "",
      contact: brand.contact ?? "",
      color: brand.color ?? "",
      intro: brand.intro ?? "",
    });
  }, [brand]);

  async function send(url: string, init: RequestInit) {
    setFailure(null);
    setSaved(false);
    const resp = await fetch(url, init);
    const body = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      setFailure(typeof body.detail === "string" ? body.detail : "No se ha podido guardar");
      return;
    }
    setBrand(body as BrandingOut);
    setSaved(true);
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    const values = Object.fromEntries(
      Object.entries(form).map(([k, v]) => [k, v.trim() ? v : null]),
    );
    await send("/api/branding", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    });
  }

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const content = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result).split(",")[1] ?? "");
      reader.onerror = () => reject(reader.error);
      reader.readAsDataURL(file);
    });
    await send("/api/branding/logo", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content_base64: content }),
    });
    event.target.value = "";
  }

  const field = (id: keyof typeof form) => ({
    id: `brand-${id}`,
    value: form[id],
    onChange: (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setForm((f) => ({ ...f, [id]: e.target.value })),
  });

  return (
    <div className="branding">
      <form className="branding-form" onSubmit={save}>
        <div className="field">
          <label htmlFor="brand-display_name">Nombre comercial</label>
          <input maxLength={80} {...field("display_name")} />
        </div>
        <div className="field">
          <label htmlFor="brand-contact">Contacto</label>
          <input maxLength={120} placeholder="Teléfono, correo o web" {...field("contact")} />
        </div>
        <div className="field">
          <label htmlFor="brand-color">Color principal</label>
          <input placeholder="#1f5f8b" maxLength={7} {...field("color")} />
          <span className="hint">Tiene que leerse bien sobre blanco: se comprueba al guardar.</span>
        </div>
        <div className="field">
          <label htmlFor="brand-intro">Presentación</label>
          <textarea rows={4} maxLength={600} {...field("intro")} />
        </div>
        {failure && <p className="failure" role="alert">{failure}</p>}
        {saved && <p className="hint">Guardado.</p>}
        <button type="submit">Guardar</button>
      </form>
      <div className="field">
        <label htmlFor="brand-logo">Logotipo (PNG o JPEG, hasta 2 MB)</label>
        <input id="brand-logo" type="file" accept="image/png,image/jpeg" onChange={upload} />
        {brand?.has_logo && (
          <button type="button" className="link"
                  onClick={() => send("/api/branding/logo", { method: "DELETE" })}>
            Quitar el logotipo
          </button>
        )}
      </div>
      <h2>Así se verá en tus planes</h2>
      <BrandHeader brand={brand} version={version} />
      {brand && !(brand.display_name || brand.contact || brand.intro || brand.has_logo) && (
        <p className="empty">Sin marca: los planes salen como hasta ahora.</p>
      )}
    </div>
  );
}
