"use client";

import "maplibre-gl/dist/maplibre-gl.css";

import { layers, namedFlavor, type Flavor } from "@protomaps/basemaps";
import * as maplibregl from "maplibre-gl";
import type { GeoJSONSource, MapLayerMouseEvent, Map as MapLibre, StyleSpecification } from "maplibre-gl";
import { PMTiles, Protocol } from "pmtiles";
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
const MADRID: [number, number] = [-3.7, 40.42];
const SOURCE = {
  catastro: "Catastro",
  cartociudad: "CartoCiudad",
  canal: "el propio anuncio",
} as Record<string, string>;

type Place = ScoredOut & { lon: number; lat: number };
/** Lo que cubre el extracto de teselas (`make mapa`): fuera de ahí no hay mapa que enseñar. */
type Bounds = [[number, number], [number, number]];

let protocol: Protocol | null = null;

const inside = (b: Bounds | null, p: Place) =>
  !b || (p.lon >= b[0][0] && p.lon <= b[1][0] && p.lat >= b[0][1] && p.lat <= b[1][1]);

/** Mezcla de dos colores #rrggbb: el relieve del mapa sale de la paleta, no de otra. */
function mix(a: string, b: string, amount: number): string {
  const rgb = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  if (!/^#[0-9a-f]{6}$/i.test(a) || !/^#[0-9a-f]{6}$/i.test(b)) return a;
  const [x, y] = [rgb(a), rgb(b)];
  return `#${x.map((v, i) => Math.round(v + (y[i] - v) * amount).toString(16).padStart(2, "0")).join("")}`;
}

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
    // El campo y el monte, apenas insinuados: sin esto el mapa claro sale moteado de verdes ajenos
    landcover: {
      barren: t.canvas,
      farmland: mix(t.canvas, t.sunk, 0.35),
      forest: mix(t.canvas, t.pass, 0.12),
      glacier: t.raised,
      grassland: mix(t.canvas, t.pass, 0.06),
      scrub: mix(t.canvas, t.pass, 0.08),
      urban_area: mix(t.canvas, t.raised2, 0.6),
    },
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

type Failure = { status: number; text: string };

/** Qué hacer cuando no hay búsqueda: sin cliente, a Clientes; con el perfil a medias, al perfil. */
function failureAction(f: Failure): { title: string; text: string; href: string | null; cta: string | null } {
  if (f.status === 409)
    return f.text.startsWith("Elige")
      ? { title: "Elige un cliente", text: "Arriba, en Cliente. El mapa se rehace con su plan en cada oferta.", href: null, cta: null }
      : {
          title: "¿Para quién buscas?",
          text: "El mapa enseña el plan de cada cliente en cada oferta: si encaja, su cash flow y si es subasta. Empieza por crear el primero.",
          href: "/clientes",
          cta: "Crear un cliente",
        };
  if (f.status === 404 || f.status === 422)
    return { title: "Falta el perfil", text: f.text, href: "/perfil", cta: "Completar el perfil" };
  return { title: "No se ha podido buscar", text: f.text, href: null, cta: null };
}

export function OfferMap() {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<MapLibre | null>(null);
  const [result, setResult] = useState<SearchOut | null>(null);
  const [failure, setFailure] = useState<Failure | null>(null);
  const [onlyPass, setOnlyPass] = useState(false);
  const [onlyAuction, setOnlyAuction] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [view, setView] = useState<"mapa" | "lista">("mapa");
  const [here, setHere] = useState<[number, number] | null>(null);
  const [locating, setLocating] = useState(false);
  const [locateError, setLocateError] = useState<string | null>(null);
  const [baseMissing, setBaseMissing] = useState(false);
  const [coverage, setCoverage] = useState<Bounds | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const resp = await fetch("/api/search");
        const body = await resp.json().catch(() => ({}));
        if (resp.ok) setResult(body as SearchOut);
        else if (resp.status === 404)
          setFailure({ status: 404, text: "Con tu perfil confirmado se calcula tu plan en cada oferta." });
        else if (resp.status === 422 && Array.isArray(body.detail))
          setFailure({ status: 422, text: `Falta en tu perfil: ${body.detail.join(", ")}.` });
        else
          setFailure({
            status: resp.status,
            text: typeof body.detail === "string" ? body.detail : "La búsqueda no ha respondido. Vuelve a cargar la página.",
          });
      } catch {
        setFailure({ status: 0, text: "No se ha podido conectar con la API." });
      }
    })();
  }, []);

  const located = useMemo(
    () => (result?.ranked ?? []).filter((s): s is Place => s.lon != null && s.lat != null),
    [result],
  );
  const places = useMemo(
    () => located.filter((s) => (!onlyPass || s.passes) && (!onlyAuction || s.auction)),
    [located, onlyPass, onlyAuction],
  );
  // En el mapa, solo lo que cae dentro de las teselas; lo de fuera sigue en la lista
  const onMap = useMemo(() => places.filter((p) => inside(coverage, p)), [places, coverage]);
  const onMapRef = useRef<Place[]>([]);
  onMapRef.current = onMap;
  const hereRef = useRef(here);
  hereRef.current = here;
  const coverageRef = useRef(coverage);
  coverageRef.current = coverage;

  // El mapa se crea una vez; con el tema se repinta entero
  useEffect(() => {
    if (!box.current || map.current) return;
    if (!protocol) {
      maplibregl.setWorkerUrl(`${window.location.origin}/mapa/maplibre-gl-worker.mjs`);
      protocol = new Protocol();
      maplibregl.addProtocol("pmtiles", protocol.tile);
    }
    const archive = new PMTiles(`${window.location.origin}${TILES}`);
    protocol.add(archive);
    const m = new maplibregl.Map({
      container: box.current,
      style: baseStyle(readTheme()),
      center: MADRID,
      zoom: 9,
      attributionControl: { compact: true },
      cooperativeGestures: false,
    });
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    // El mapa no sale de lo que cubren las teselas: sin esto, al alejarse se ve una franja cortada
    archive
      .getHeader()
      .then((h) => {
        const b: Bounds = [
          [h.minLon, h.minLat],
          [h.maxLon, h.maxLat],
        ];
        setCoverage(b);
        m.setMaxBounds(b);
        if (!framed.current) m.fitBounds(b, { duration: 0 });
      })
      .catch(() => setBaseMissing(true));
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
      addOffers(m, t, onMapRef.current);
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
    source?.setData(geojson(onMap));
  }, [onMap]);

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
        const b = coverageRef.current;
        if (b && !inside(b, { lon: point[0], lat: point[1] } as Place)) {
          if (!quiet) setLocateError("Estás fuera de la zona que cubre el mapa.");
          return;
        }
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
    const shown = located.filter((p) => inside(coverage, p));
    if (shown.length === 0) return; // sin ofertas en el mapa, se queda encuadrado en las teselas
    framed.current = true;
    if (shown.length === 1) m.jumpTo({ center: [shown[0].lon, shown[0].lat], zoom: 13 });
    else {
      const bounds = new maplibregl.LngLatBounds();
      shown.forEach((p) => bounds.extend([p.lon, p.lat]));
      m.fitBounds(bounds, { padding: framePadding(), maxZoom: 14, duration: still() ? 0 : 900 });
    }
    navigator.permissions
      ?.query({ name: "geolocation" as PermissionName })
      .then((p) => p.state === "granted" && locate(true))
      .catch(() => undefined);
  }, [result, located, coverage, locate]);

  const select = useCallback((id: string) => {
    setSelected(id);
    setView("mapa");
    const p = onMapRef.current.find((x) => x.offer_id === id);
    if (p && map.current) {
      // el punto queda en el hueco libre: ni debajo del panel ni debajo de la ficha que se abre
      const pad = framePadding();
      const wide = matchMedia("(min-width: 921px)").matches;
      map.current.flyTo({
        center: [p.lon, p.lat],
        zoom: Math.max(map.current.getZoom(), 14),
        padding: { ...pad, bottom: wide ? 280 : 340 },
        duration: still() ? 0 : 800,
        essential: true,
      });
    }
  }, []);

  const chosen = places.find((p) => p.offer_id === selected) ?? null;
  const total = result?.ranked.length ?? 0;
  const unlocated = total - located.length;
  const outside = places.length - onMap.length;
  const passing = places.filter((p) => p.passes).length;
  const auctions = places.filter((p) => p.auction).length;
  const filtered = onlyPass || onlyAuction;
  const action = failure ? failureAction(failure) : null;

  return (
    <div className={`offer-map view-${view}`}>
      <button
        type="button"
        className="map-tool map-toggle"
        onClick={() => setView((v) => (v === "mapa" ? "lista" : "mapa"))}
      >
        {view === "mapa" ? "Ver la lista" : "Ver el mapa"}
      </button>

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
        {chosen && <OfferSheet offer={chosen} offMap={!inside(coverage, chosen)} onClose={() => setSelected(null)} />}
      </div>

      <aside className={`map-panel${places.length === 0 ? " is-short" : ""}`} aria-label="Ofertas de la búsqueda">
        <header className="map-panel-head">
          <h2 className="map-panel-title">
            {action ? action.title : result ? (places.length === 1 ? "1 oferta" : `${places.length} ofertas`) : "Ofertas"}
          </h2>
          {result && places.length > 0 && (
            <p className="map-panel-sub">
              {passing === 1 ? "1 encaja" : `${passing} encajan`} con el plan
              {auctions > 0 && ` · ${auctions === 1 ? "1 subasta" : `${auctions} subastas`}`}
            </p>
          )}
        </header>

        {result && total > 0 && (
          <div className="map-filters" role="group" aria-label="Filtros">
            <button type="button" className="chip" aria-pressed={onlyPass} onClick={() => setOnlyPass((v) => !v)}>
              Solo las que encajan
            </button>
            <button type="button" className="chip" aria-pressed={onlyAuction} onClick={() => setOnlyAuction((v) => !v)}>
              Subastas
            </button>
          </div>
        )}

        <div className="map-panel-body">
          {!result && !failure && <Skeleton label="Calculando el plan en cada oferta…" shape="text" />}

          {failure && action && (
            <div className="map-empty">
              <p>{action.text}</p>
              {action.href && (
                <a className="button-link primary" href={action.href}>
                  {action.cta}
                </a>
              )}
            </div>
          )}

          {result && places.length === 0 && (
            <div className="map-empty">
              <h3>{filtered ? "Ninguna con estos filtros" : "Aún no hay ofertas"}</h3>
              <p>
                {filtered
                  ? "Quita un filtro para ver el resto."
                  : "Pega un anuncio o espera a la próxima lectura del BOE y del Portal de Subastas."}
              </p>
              {filtered ? (
                <button
                  type="button"
                  className="button-link"
                  onClick={() => {
                    setOnlyPass(false);
                    setOnlyAuction(false);
                  }}
                >
                  Quitar los filtros
                </button>
              ) : (
                <a className="button-link primary" href="/ofertas">
                  Añadir un anuncio
                </a>
              )}
            </div>
          )}

          <ol className="map-items">
            {places.map((p) => {
              const cash = fig(p, "cashflow.monthly_after_tax");
              const price = fig(p, "offer.price");
              const off = !inside(coverage, p);
              return (
                <li key={p.offer_id}>
                  <button type="button" aria-current={p.offer_id === selected} onClick={() => select(p.offer_id)}>
                    <span className="map-item-top">
                      <span className={p.passes ? "status pass" : "status fail"}>{p.passes ? "Encaja" : "No encaja"}</span>
                      {p.auction && <span className="map-tag">Subasta</span>}
                      {off && <span className="map-tag quiet">Fuera del mapa</span>}
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
        </div>

        <footer className="map-panel-foot">
          {places.length > 0 && (
            <span className="map-legend" aria-hidden="true">
              <span className="status pass">Encaja</span>
              <span className="status fail">No encaja</span>
            </span>
          )}
          {(unlocated > 0 || outside > 0) && (
            <span className="hint">
              {[unlocated > 0 && `${unlocated} sin ubicar`, outside > 0 && `${outside} fuera del mapa`]
                .filter(Boolean)
                .join(" · ")}
            </span>
          )}
          <a className="map-add" href="/ofertas">
            <svg viewBox="0 0 20 20" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
              <path d="M10 4v12M4 10h12" />
            </svg>
            Añadir un anuncio
          </a>
        </footer>
      </aside>
    </div>
  );
}

/** Margen al encuadrar: en escritorio el panel tapa la izquierda del mapa. */
function framePadding() {
  const panel = document.querySelector(".map-panel");
  const wide = matchMedia("(min-width: 921px)").matches;
  const left = wide && panel ? panel.getBoundingClientRect().right - (panel.parentElement?.getBoundingClientRect().left ?? 0) + 32 : 48;
  return { top: 72, right: 72, bottom: 72, left };
}

function OfferSheet({ offer, offMap, onClose }: { offer: Place; offMap: boolean; onClose: () => void }) {
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
        <p className="hint">
          Ubicación: {SOURCE[offer.location_source] ?? offer.location_source}.
          {offMap && " Queda fuera de la zona que cubre el mapa."}
        </p>
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
