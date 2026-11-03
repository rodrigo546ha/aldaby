"use client";

import "maplibre-gl/dist/maplibre-gl.css";

import { layers, namedFlavor, type Flavor } from "@protomaps/basemaps";
import * as maplibregl from "maplibre-gl";
import type { GeoJSONSource, MapLayerMouseEvent, Map as MapLibre, StyleSpecification } from "maplibre-gl";
import { Protocol } from "pmtiles";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { components } from "../lib/api-types";
import { formatValue, type FigureOut } from "../lib/format";
import { Amount } from "./FigureView";
import { Skeleton } from "./Motion";

type SearchOut = components["schemas"]["SearchOut"];
type ScoredOut = components["schemas"]["ScoredOut"];

// Mapa de ofertas (ADR-0051): teselas propias de OpenStreetMap con los colores de Aldaby, y las
// ofertas de la búsqueda inversa donde están. La web pinta lo que devuelve la API, no calcula nada.

const TILES = "/mapa/teselas.pmtiles";
const SPAIN: [number, number] = [-3.7, 40.4];
const SOURCE = {
  catastro: "Catastro",
  cartociudad: "CartoCiudad",
  canal: "el propio anuncio",
} as Record<string, string>;

type Place = ScoredOut & { lon: number; lat: number };

let protocolAdded = false;

function readTheme() {
  const css = getComputedStyle(document.documentElement);
  const v = (name: string) => css.getPropertyValue(name).trim();
  const dark = (document.documentElement.dataset.theme ?? (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark")) === "dark";
  return {
    dark,
    canvas: v("--canvas"),
    sunk: v("--sunk"),
    raised: v("--raised"),
    raised2: v("--raised-2"),
    strong: v("--strong"),
    text: v("--text"),
    muted: v("--muted"),
    pass: v("--pass"),
    mark: v("--mark"),
    stat: v("--stat"),
  };
}

type Theme = ReturnType<typeof readTheme>;

/** Las capas de Protomaps con la paleta de Aldaby: el mapa es fondo, no protagonista. */
function baseStyle(t: Theme): StyleSpecification {
  const flavor: Flavor = {
    ...namedFlavor(t.dark ? "dark" : "light"),
    background: t.canvas,
    earth: t.canvas,
    water: t.sunk,
    park_a: t.raised,
    park_b: t.raised,
    wood_a: t.raised,
    wood_b: t.raised,
    scrub_a: t.raised,
    scrub_b: t.raised,
    buildings: t.raised2,
    city_label: t.text,
    city_label_halo: t.canvas,
    subplace_label: t.muted,
    subplace_label_halo: t.canvas,
    roads_label_minor: t.muted,
    roads_label_minor_halo: t.canvas,
    roads_label_major: t.text,
    roads_label_major_halo: t.canvas,
    state_label: t.muted,
    state_label_halo: t.canvas,
    country_label: t.muted,
    ocean_label: t.muted,
    address_label: t.muted,
    address_label_halo: t.canvas,
  };
  delete flavor.pois; // sin iconos de puntos de interés: no hay sprites propios
  return {
    version: 8,
    glyphs: `${window.location.origin}/mapa/fonts/{fontstack}/{range}.pbf`,
    sources: {
      osm: {
        type: "vector",
        url: `pmtiles://${window.location.origin}${TILES}`,
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      },
    },
    layers: layers("osm", flavor, { lang: "es" }),
  };
}

const fig = (s: ScoredOut, key: string): FigureOut | undefined => s.figures.find((f) => f.key === key);
const title = (s: ScoredOut) => s.title ?? (s.kind === "enlace" ? "Oferta pegada" : "Lote del BOE");

/** El texto de la pastilla: el cash flow del usuario, que es lo que decide, no el precio. */
function pill(s: ScoredOut): string {
  const f = fig(s, "cashflow.monthly_after_tax");
  return f ? formatValue(f.value, f.unit).replace(" al mes", "/mes") : "";
}

function geojson(places: Place[]) {
  return {
    type: "FeatureCollection" as const,
    features: places.map((p) => ({
      type: "Feature" as const,
      geometry: { type: "Point" as const, coordinates: [p.lon, p.lat] },
      properties: { id: p.offer_id, passes: p.passes, label: pill(p) },
    })),
  };
}

function addOffers(map: MapLibre, t: Theme, places: Place[]) {
  map.addSource("ofertas", {
    type: "geojson",
    data: geojson(places),
    cluster: true,
    clusterRadius: 44,
    clusterMaxZoom: 14,
  });
  map.addLayer({
    id: "grupos",
    type: "circle",
    source: "ofertas",
    filter: ["has", "point_count"],
    paint: {
      "circle-color": t.raised,
      "circle-stroke-color": t.stat,
      "circle-stroke-width": 1.5,
      "circle-radius": ["step", ["get", "point_count"], 16, 10, 20, 50, 26],
    },
  });
  map.addLayer({
    id: "grupos-n",
    type: "symbol",
    source: "ofertas",
    filter: ["has", "point_count"],
    layout: { "text-field": ["get", "point_count_abbreviated"], "text-font": ["Noto Sans Medium"], "text-size": 13 },
    paint: { "text-color": t.strong },
  });
  // Lleno si encaja con el plan, hueco si no: la misma marca que en toda la web
  map.addLayer({
    id: "puntos",
    type: "circle",
    source: "ofertas",
    filter: ["!", ["has", "point_count"]],
    paint: {
      "circle-radius": 7,
      "circle-color": ["case", ["get", "passes"], t.pass, t.canvas],
      "circle-stroke-color": ["case", ["get", "passes"], t.pass, t.mark],
      "circle-stroke-width": 2.5,
    },
  });
  map.addLayer({
    id: "puntos-texto",
    type: "symbol",
    source: "ofertas",
    filter: ["!", ["has", "point_count"]],
    layout: {
      "text-field": ["get", "label"],
      "text-font": ["Noto Sans Medium"],
      "text-size": 12,
      "text-offset": [0, -1.5],
      "text-anchor": "bottom",
      "text-allow-overlap": false,
    },
    paint: { "text-color": t.strong, "text-halo-color": t.canvas, "text-halo-width": 1.6 },
  });
}

function addHere(map: MapLibre, t: Theme, here: [number, number] | null) {
  if (!here) return;
  map.addSource("aqui", { type: "geojson", data: { type: "Point", coordinates: here } });
  map.addLayer({
    id: "aqui",
    type: "circle",
    source: "aqui",
    paint: { "circle-radius": 6, "circle-color": t.stat, "circle-stroke-color": t.canvas, "circle-stroke-width": 3 },
  });
}

const still = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

export function OfferMap() {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<MapLibre | null>(null);
  const [result, setResult] = useState<SearchOut | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [onlyPass, setOnlyPass] = useState(false);
  const [onlyAuction, setOnlyAuction] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [view, setView] = useState<"mapa" | "lista">("mapa");
  const [here, setHere] = useState<[number, number] | null>(null);
  const [locating, setLocating] = useState(false);
  const [locateError, setLocateError] = useState<string | null>(null);
  const [baseMissing, setBaseMissing] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const resp = await fetch("/api/search");
        const body = await resp.json().catch(() => ({}));
        if (resp.ok) setResult(body as SearchOut);
        else if (resp.status === 404) setFailure("Confirma primero tu perfil: con él se calcula tu plan en cada oferta.");
        else if (resp.status === 422 && Array.isArray(body.detail)) setFailure(`Falta en tu perfil: ${body.detail.join(", ")}.`);
        else setFailure(typeof body.detail === "string" ? body.detail : "No se ha podido hacer la búsqueda.");
      } catch {
        setFailure("No se ha podido conectar con la API.");
      }
    })();
  }, []);

  const places = useMemo(
    () =>
      (result?.ranked ?? [])
        .filter((s): s is Place => s.lon != null && s.lat != null)
        .filter((s) => (!onlyPass || s.passes) && (!onlyAuction || s.auction)),
    [result, onlyPass, onlyAuction],
  );
  const placesRef = useRef<Place[]>([]);
  placesRef.current = places;
  const hereRef = useRef(here);
  hereRef.current = here;

  // El mapa se crea una vez; con el tema se repinta entero
  useEffect(() => {
    if (!box.current || map.current) return;
    if (!protocolAdded) {
      maplibregl.setWorkerUrl(`${window.location.origin}/mapa/maplibre-gl-worker.mjs`);
      maplibregl.addProtocol("pmtiles", new Protocol().tile);
      protocolAdded = true;
    }
    fetch(TILES, { method: "HEAD" })
      .then((r) => setBaseMissing(!r.ok))
      .catch(() => setBaseMissing(true));
    const m = new maplibregl.Map({
      container: box.current,
      style: baseStyle(readTheme()),
      center: SPAIN,
      zoom: 5,
      attributionControl: { compact: true },
      cooperativeGestures: false,
    });
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    // Sin sprites propios: las ciudades llevan un punto dibujado aquí y los escudos de carretera, nada
    m.setMissingStyleImageResolver((id) => {
      if (m.hasImage(id)) return;
      const size = 12;
      const dot = document.createElement("canvas");
      dot.width = dot.height = size;
      const ctx = dot.getContext("2d");
      if (!ctx) return;
      if (id === "capital" || id === "townspot") {
        ctx.fillStyle = readTheme().muted;
        ctx.beginPath();
        ctx.arc(size / 2, size / 2, id === "capital" ? 5 : 3.5, 0, Math.PI * 2);
        ctx.fill();
      }
      m.addImage(id, ctx.getImageData(0, 0, size, size), { pixelRatio: 2 });
    });
    const paint = () => {
      const t = readTheme();
      addOffers(m, t, placesRef.current);
      addHere(m, t, hereRef.current);
    };
    m.on("style.load", paint);
    m.on("click", "puntos", (e: MapLayerMouseEvent) => {
      const id = e.features?.[0]?.properties?.id as string | undefined;
      if (id) setSelected(id);
    });
    m.on("click", "grupos", async (e: MapLayerMouseEvent) => {
      const feature = e.features?.[0];
      const source = m.getSource("ofertas") as GeoJSONSource | undefined;
      if (!feature || !source) return;
      const zoom = await source.getClusterExpansionZoom(feature.properties?.cluster_id as number);
      m.easeTo({ center: (feature.geometry as GeoJSON.Point).coordinates as [number, number], zoom, duration: still() ? 0 : 500 });
    });
    for (const id of ["puntos", "grupos"]) {
      m.on("mouseenter", id, () => (m.getCanvas().style.cursor = "pointer"));
      m.on("mouseleave", id, () => (m.getCanvas().style.cursor = ""));
    }
    map.current = m;
    const repaint = () => m.setStyle(baseStyle(readTheme()));
    const themes = new MutationObserver(repaint);
    themes.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    const scheme = matchMedia("(prefers-color-scheme: light)");
    scheme.addEventListener("change", repaint);
    return () => {
      themes.disconnect();
      scheme.removeEventListener("change", repaint);
      m.remove();
      map.current = null;
    };
  }, []);

  // Las ofertas (y los filtros) cambian los datos, no el estilo
  useEffect(() => {
    const source = map.current?.getSource("ofertas") as GeoJSONSource | undefined;
    source?.setData(geojson(places));
  }, [places]);

  // Al llegar las ofertas, el mapa las encuadra; si ya diste permiso de ubicación, centra en ti
  const framed = useRef(false);
  const locate = useCallback((quiet = false) => {
    if (!("geolocation" in navigator)) {
      if (!quiet) setLocateError("Este navegador no da la ubicación.");
      return;
    }
    setLocating(true);
    setLocateError(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const point: [number, number] = [pos.coords.longitude, pos.coords.latitude];
        setHere(point);
        setLocating(false);
        const m = map.current;
        if (!m) return;
        const source = m.getSource("aqui") as GeoJSONSource | undefined;
        if (source) source.setData({ type: "Point", coordinates: point });
        else addHere(m, readTheme(), point);
        m.flyTo({ center: point, zoom: 13, duration: still() ? 0 : 1600, essential: true });
      },
      () => {
        setLocating(false);
        if (!quiet) setLocateError("No se ha podido saber dónde estás. Revisa el permiso de ubicación.");
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 },
    );
  }, []);

  useEffect(() => {
    const m = map.current;
    if (!m || !result || framed.current) return;
    framed.current = true;
    const all = (result.ranked ?? []).filter((s): s is Place => s.lon != null && s.lat != null);
    if (all.length === 1) m.jumpTo({ center: [all[0].lon, all[0].lat], zoom: 13 });
    else if (all.length > 1) {
      const bounds = new maplibregl.LngLatBounds();
      all.forEach((p) => bounds.extend([p.lon, p.lat]));
      m.fitBounds(bounds, { padding: 64, maxZoom: 14, duration: still() ? 0 : 900 });
    }
    navigator.permissions
      ?.query({ name: "geolocation" as PermissionName })
      .then((p) => p.state === "granted" && locate(true))
      .catch(() => undefined);
  }, [result, locate]);

  const select = useCallback((id: string) => {
    setSelected(id);
    setView("mapa");
    const p = placesRef.current.find((x) => x.offer_id === id);
    if (p && map.current) {
      map.current.flyTo({ center: [p.lon, p.lat], zoom: Math.max(map.current.getZoom(), 14), duration: still() ? 0 : 800, essential: true });
    }
  }, []);

  const chosen = places.find((p) => p.offer_id === selected) ?? null;
  const unlocated = (result?.ranked ?? []).length - (result?.ranked ?? []).filter((s) => s.lon != null).length;

  return (
    <div className={`offer-map view-${view}`}>
      <button
        type="button"
        className="map-tool map-toggle"
        onClick={() => setView((v) => (v === "mapa" ? "lista" : "mapa"))}
      >
        {view === "mapa" ? "Ver la lista" : "Ver el mapa"}
      </button>
      <aside className="map-list" aria-label="Ofertas de la búsqueda">
        <div className="map-filters" role="group" aria-label="Filtros">
          <button type="button" className="chip" aria-pressed={onlyPass} onClick={() => setOnlyPass((v) => !v)}>
            Solo las que encajan
          </button>
          <button type="button" className="chip" aria-pressed={onlyAuction} onClick={() => setOnlyAuction((v) => !v)}>
            Subastas
          </button>
          <a className="chip" href="/ofertas">
            Añadir un anuncio
          </a>
        </div>
        {!result && !failure && <Skeleton label="Calculando tu plan en cada oferta…" shape="text" />}
        {failure && (
          <p className="failure">
            {failure} <a href="/perfil">Ir a tu perfil</a>
          </p>
        )}
        {result && (
          <p className="map-count">
            {places.length === 1 ? "1 oferta" : `${places.length} ofertas`}
            {unlocated > 0 && ` · ${unlocated} sin ubicar`}
          </p>
        )}
        <ol className="map-items">
          {places.map((p) => {
            const cash = fig(p, "cashflow.monthly_after_tax");
            const price = fig(p, "offer.price");
            return (
              <li key={p.offer_id}>
                <button type="button" aria-current={p.offer_id === selected} onClick={() => select(p.offer_id)}>
                  <span className={p.passes ? "status pass" : "status fail"}>
                    {p.passes ? "Encaja" : "No encaja"}
                    {p.auction ? " · subasta" : ""}
                  </span>
                  <span className="map-item-title">{title(p)}</span>
                  <span className="map-item-figures">
                    {cash && (
                      <strong>
                        <Amount text={formatValue(cash.value, cash.unit)} />
                      </strong>
                    )}
                    {price && <span>{formatValue(price.value, price.unit)}</span>}
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
      </aside>

      <div className="map-stage">
        <div ref={box} className="map-canvas" role="region" aria-label="Mapa de las ofertas" />
        {baseMissing && (
          <p className="map-notice" role="status">
            Falta el mapa base: genera las teselas con <code>make mapa</code>.
          </p>
        )}
        <div className="map-tools">
          <button type="button" className="map-tool" onClick={() => locate(false)} disabled={locating} aria-busy={locating}>
            <svg viewBox="0 0 20 20" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
              <circle cx="10" cy="10" r="4" />
              <path d="M10 1.5v3M10 15.5v3M1.5 10h3M15.5 10h3" />
            </svg>
            {locating ? "Buscándote…" : "Centrar en mí"}
          </button>
        </div>
        {locateError && (
          <p className="map-notice" role="alert">
            {locateError}
          </p>
        )}
        {chosen && <OfferSheet offer={chosen} onClose={() => setSelected(null)} />}
      </div>
    </div>
  );
}

function OfferSheet({ offer, onClose }: { offer: Place; onClose: () => void }) {
  const close = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    close.current?.focus({ preventScroll: true });
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [offer.offer_id, onClose]);
  const shown = [
    ["cashflow.monthly_after_tax", "Tu cash flow"],
    ["offer.price", "Precio"],
    ["irr.rate", "TIR"],
  ] as const;
  return (
    <section className="offer-sheet" aria-labelledby="ficha-titulo">
      <div className="offer-sheet-head">
        <span className={offer.passes ? "status pass" : "status fail"}>
          {offer.passes ? "Encaja con tu plan" : "No encaja con tu plan"}
          {offer.auction ? " · subasta" : ""}
        </span>
        <button ref={close} type="button" className="sheet-close" onClick={onClose} aria-label="Cerrar la ficha">
          <svg viewBox="0 0 20 20" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
            <path d="M5 5l10 10M15 5 5 15" />
          </svg>
        </button>
      </div>
      <h2 id="ficha-titulo" title={title(offer)}>
        {title(offer)}
      </h2>
      <div className="offer-sheet-figures">
        {shown.map(([key, label]) => {
          const f = fig(offer, key);
          return f ? (
            <div key={key}>
              <span className="verdict-label">{label}</span>
              <span className="sheet-value">
                <Amount text={formatValue(f.value, f.unit)} />
              </span>
            </div>
          ) : null;
        })}
      </div>
      {offer.reasons.length > 0 && <p className="verdict-reason">{offer.reasons.join(". ")}.</p>}
      {offer.location_source && (
        <p className="hint">Ubicación: {SOURCE[offer.location_source] ?? offer.location_source}.</p>
      )}
      <div className="verdict-actions">
        <a className="button-link primary" href={`/plan/${offer.offer_id}`}>
          Ver mi plan
        </a>
        {offer.url && (
          <a href={offer.url} target="_blank" rel="noreferrer">
            Ver la oferta
          </a>
        )}
      </div>
    </section>
  );
}
