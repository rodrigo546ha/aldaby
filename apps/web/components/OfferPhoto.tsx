"use client";

import { useState } from "react";

// Imagen de una oferta (ADR-0054): la del anuncio pegado, la foto de fachada del Catastro o la
// ortofoto del PNOA, por ese orden. La API responde 404 si no hay; entonces se prueba la siguiente
// y, sin ninguna, queda el dibujo del tipo de inmueble.

type Kind = "fachada" | "aerea";

const CREDIT: Record<Kind | "anuncio", string> = {
  anuncio: "Foto del anuncio",
  fachada: "Foto: Dirección General del Catastro",
  aerea: "Ortofoto PNOA · CC BY 4.0 scne.es",
};

export function OfferPhoto({
  offerId,
  kinds = ["fachada", "aerea"],
  images = [],
  propertyType,
  credit = false,
  hideEmpty = false,
  className = "",
}: {
  offerId: string;
  kinds?: Kind[];
  images?: string[];
  propertyType?: string | null;
  credit?: boolean;
  hideEmpty?: boolean; // sin ninguna imagen, nada (en vez del dibujo del tipo)
  className?: string;
}) {
  const sources = [
    ...images.slice(0, 1).map((src) => ({ src, kind: "anuncio" as const })),
    ...kinds.map((kind) => ({ src: `/api/offers/${offerId}/photo/${kind}`, kind })),
  ];
  const key = `${offerId}|${sources.map((s) => s.src).join(",")}`;
  // Otra oferta, otra lista de imágenes: se empieza por la primera (sin efecto, que llegaría tarde)
  const [state, setState] = useState({ key, index: 0, loaded: false });
  if (state.key !== key) setState({ key, index: 0, loaded: false });
  const { index, loaded } = state.key === key ? state : { index: 0, loaded: false };
  const setLoaded = (value: boolean) => setState((s) => ({ ...s, loaded: value }));
  const next = () => setState((s) => ({ ...s, index: s.index + 1, loaded: false }));

  const current = sources[index];
  if (!current && hideEmpty) return null;
  return (
    <figure className={`offer-photo ${className}${loaded ? " is-loaded" : ""}`}>
      {current ? (
        <img
          key={current.src}
          src={current.src}
          alt=""
          loading="lazy"
          decoding="async"
          referrerPolicy="no-referrer"
          // Desde la caché del navegador la imagen puede estar lista antes que el onLoad
          ref={(img) => {
            if (img?.complete && img.naturalWidth > 0 && !loaded) setLoaded(true);
          }}
          onLoad={() => setLoaded(true)}
          onError={next}
        />
      ) : (
        <TypeIcon type={propertyType} />
      )}
      {credit && current && loaded && <figcaption>{CREDIT[current.kind]}</figcaption>}
    </figure>
  );
}

/** Dibujo del tipo de inmueble cuando no hay ninguna imagen pública. */
function TypeIcon({ type }: { type?: string | null }) {
  const common = { fill: "none", stroke: "currentColor", strokeWidth: 1.4, strokeLinecap: "round", strokeLinejoin: "round" } as const;
  const rural = type === "rustica" || type === "suelo";
  return (
    <svg className="offer-photo-icon" viewBox="0 0 48 48" aria-hidden="true" {...common}>
      {rural ? (
        <>
          <path d="M4 36h40M8 36c4-6 8-9 14-9s12 3 18 9" />
          <path d="M14 22v-6M14 16c-3 0-4-3-4-5 2 0 4 1 4 5Zm0 0c3 0 4-3 4-5-2 0-4 1-4 5Z" />
        </>
      ) : type === "garaje" || type === "trastero" ? (
        <>
          <path d="M6 40V18l18-10 18 10v22" />
          <path d="M13 40V26h22v14M13 31h22M13 36h22" />
        </>
      ) : (
        <>
          <path d="M8 40V12h20v28M28 20h12v20M4 40h40" />
          <path d="M13 18h4M19 18h4M13 25h4M19 25h4M13 32h4M19 32h4M33 26h3M33 32h3" />
        </>
      )}
    </svg>
  );
}
