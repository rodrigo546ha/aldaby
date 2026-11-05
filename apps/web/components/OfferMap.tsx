"use client";

import "maplibre-gl/dist/maplibre-gl.css";

import { layers, namedFlavor, type Flavor } from "@protomaps/basemaps";
import * as maplibregl from "maplibre-gl";
import type { GeoJSONSource, MapLayerMouseEvent, Map as MapLibre, StyleSpecification } from "maplibre-gl";
import { PMTiles, Protocol } from "pmtiles";
import { useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";

import type { components } from "../lib/api-types";
import { useApi } from "../lib/data";
import { formatValue, type FigureOut } from "../lib/format";
import { CHANNEL, channelStyle, ending, formatArea, type Channel, type Group } from "../lib/offers";
import { Amount } from "./FigureView";
import { Icon } from "./Icon";
import { Skeleton } from "./Motion";
import { OfferPhoto } from "./OfferPhoto";
import { AppLink, DATA } from "./AppLink";

type SearchOut = components["schemas"]["SearchOut"];
type ScoredOut = components["schemas"]["ScoredOut"];
type CatalogOut = components["schemas"]["CatalogOut"];

// Ofertas (ADR-0051 y ADR-0054): una sola lista de inmuebles, venga del canal que venga, en el mapa
// y en la lista. El catálogo se ve siempre; con el perfil confirmado, cada oferta lleva además el
// plan del usuario (la búsqueda inversa). La web pinta lo que devuelve la API, no calcula nada.

const TILES = "/mapa/teselas.pmtiles";
const MADRID: [number, number] = [-3.7, 40.42];

const GROUPS: { id: Group; label: string }[] = [
  { id: "todas", label: "Todas" },
  { id: "subastas", label: "Subastas" },
  { id: "directas", label: "Ventas directas" },
  { id: "agencias", label: "Agencias" },
  { id: "tuyos", label: "Tus anuncios" },
];
type TypeGroup = "todos" | "viviendas" | "locales" | "garajes" | "suelo";
const TYPES: { id: TypeGroup; label: string; types: string[] }[] = [
  { id: "todos", label: "Todos los tipos", types: [] },
  { id: "viviendas", label: "Viviendas", types: ["vivienda", "edificio"] },
  { id: "locales", label: "Locales y oficinas", types: ["local", "oficina"] },
  { id: "garajes", label: "Garajes y trasteros", types: ["garaje", "trastero"] },
  { id: "suelo", label: "Suelo y fincas", types: ["suelo", "rustica"] },
];
// Primero lo que más se busca: viviendas; al final, el campo
const TYPE_ORDER: Record<string, number> = {
  vivienda: 0, edificio: 1, local: 2, oficina: 2, garaje: 3, trastero: 3, otro: 4, suelo: 5, rustica: 6,
};

type Offer = CatalogOut & {
  plan: ScoredOut | null;
  skipped: string | null; // por qué la búsqueda no puede calcular el plan de esta oferta
  rank: number; // orden de la búsqueda inversa
};
type Place = Offer & { lon: number; lat: number };
/** Lo que cubre el extracto de teselas (`make mapa`): fuera de ahí no hay mapa que enseñar. */
type Bounds = [[number, number], [number, number]];

let protocol: Protocol | null = null;

const located = (o: Offer): o is Place => o.lon != null && o.lat != null;
const inside = (b: Bounds | null, p: { lon: number; lat: number }) =>
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
    channel: Object.fromEntries(
      (Object.keys(CHANNEL) as Channel[]).map((c) => [c, v(`--ch-${c.replace("_", "-")}`)]),
    ) as Record<Channel, string>,
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

const fig = (s: ScoredOut | null, key: string): FigureOut | undefined => s?.figures.find((f) => f.key === key);
const compact = new Intl.NumberFormat("es-ES", { notation: "compact", maximumFractionDigits: 1 });

/** La pastilla del punto: el cash flow del usuario si hay plan; si no, el precio del anuncio. */
function pill(o: Offer): string {
  const f = fig(o.plan, "cashflow.monthly_after_tax");
  if (f) return formatValue(f.value, f.unit).replace(" al mes", "/mes");
  return o.price ? `${compact.format(Number(o.price))} €` : "";
}

function geojson(places: Place[]) {
  return {
    type: "FeatureCollection" as const,
    features: places.map((p) => ({
      type: "Feature" as const,
      geometry: { type: "Point" as const, coordinates: [p.lon, p.lat] },
      properties: {
        id: p.offer_id,
        channel: p.channel,
        fit: p.plan ? (p.plan.passes ? 1 : 0) : -1,
        approx: p.approximate ? 1 : 0,
        label: p.approximate ? `≈ ${pill(p)}` : pill(p),
      },
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
  // El color dice cómo se vende; el aro verde, que encaja con el plan. La pastilla lo dice en texto.
  const byChannel: unknown[] = ["match", ["get", "channel"]];
  for (const [c, color] of Object.entries(t.channel)) byChannel.push(c, color || t.mark);
  byChannel.push(t.mark);
  map.addLayer({
    id: "puntos",
    type: "circle",
    source: "ofertas",
    filter: ["!", ["has", "point_count"]],
    paint: {
      "circle-radius": 7,
      "circle-color": byChannel as maplibregl.ExpressionSpecification,
      // En el centro de su municipio, no en su sitio: el punto, apagado (y «≈» en la pastilla)
      "circle-opacity": ["case", ["==", ["get", "approx"], 1], 0.4, 1],
      "circle-stroke-color": ["case", ["==", ["get", "fit"], 1], t.pass, t.canvas],
      "circle-stroke-width": ["case", ["==", ["get", "fit"], 1], 3.5, 2],
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

type PlanState = { status: "cargando" } | { status: "ok"; result: SearchOut } | { status: "sin_plan"; code: number; text: string };

/** Sin plan la lista se ve igual; arriba, una línea dice qué falta para verlo. */
function planHint(p: PlanState): { text: string; href: string | null; cta: string | null } | null {
  if (p.status !== "sin_plan") return null;
  if (p.code === 409)
    return p.text.startsWith("Elige")
      ? { text: "Elige un cliente arriba para ver su plan en cada oferta.", href: null, cta: null }
      : { text: "Crea un cliente para ver su plan en cada oferta.", href: "/clientes", cta: "Crear un cliente" };
  if (p.code === 404 || p.code === 422)
    return { text: "Completa tu perfil y verás si cada oferta encaja contigo y tu cash flow.", href: "/perfil", cta: "Completar el perfil" };
  return { text: p.text, href: null, cta: null };
}

function sortKey(o: Offer): [number, number, number, string] {
  const fit = o.plan ? (o.plan.passes ? 0 : 1) : 2;
  return [fit, TYPE_ORDER[o.property_type ?? "otro"] ?? 4, o.rank, o.ends_on ?? "9999"];
}

function compare(a: Offer, b: Offer): number {
  const [x, y] = [sortKey(a), sortKey(b)];
  for (let i = 0; i < x.length; i++) if (x[i] !== y[i]) return x[i] < y[i] ? -1 : 1;
  return 0;
}

type Sort = "recomendadas" | "acaban" | "precio_asc" | "precio_desc";
const SORTS: { id: Sort; label: string }[] = [
  { id: "recomendadas", label: "Recomendadas" },
  { id: "acaban", label: "Acaban antes" },
  { id: "precio_asc", label: "Más baratas" },
  { id: "precio_desc", label: "Más caras" },
];

/** Sin tildes ni mayúsculas, para buscar «alcala» y encontrar «Alcalá». */
const fold = (t: string) => t.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

function sortBy(sort: Sort): (a: Offer, b: Offer) => number {
  const price = (o: Offer) => (o.price ? Number(o.price) : null);
  if (sort === "acaban") return (a, b) => (a.ends_on ?? "9999").localeCompare(b.ends_on ?? "9999") || compare(a, b);
  if (sort === "precio_asc" || sort === "precio_desc") {
    const sign = sort === "precio_asc" ? 1 : -1;
    return (a, b) => {
      const [x, y] = [price(a), price(b)];
      if (x === null || y === null) return x === y ? compare(a, b) : x === null ? 1 : -1; // sin precio, al final
      return (x - y) * sign || compare(a, b);
    };
  }
  return compare;
}

export function OfferMap() {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<MapLibre | null>(null);
  // Las ofertas y tu plan en cada una, de la caché de la app: volver al mapa es instantáneo
  const catalogApi = useApi<CatalogOut[]>("/api/offers/catalog");
  const searchApi = useApi<SearchOut>("/api/search");
  const catalog = catalogApi.result?.ok ? catalogApi.result.data : null;
  const catalogError =
    catalogApi.result && !catalogApi.result.ok
      ? catalogApi.result.status === 0
        ? "No se ha podido conectar con la API."
        : "No se han podido cargar las ofertas. Vuelve a cargar la página."
      : null;
  const searched = searchApi.result;
  const planState = useMemo<PlanState>(() => {
    if (!searched) return { status: "cargando" };
    if (searched.ok) return { status: "ok", result: searched.data };
    const text =
      typeof searched.detail === "string"
        ? searched.detail
        : searched.status === 0
          ? "No se ha podido calcular tu plan."
          : "La búsqueda no ha respondido.";
    return { status: "sin_plan", code: searched.status, text };
  }, [searched]);
  const [group, setGroup] = useState<Group>("todas");
  const [typeGroup, setTypeGroup] = useState<TypeGroup>("todos");
  const [onlyPass, setOnlyPass] = useState(false);
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<Sort>("recomendadas");
  const deferredQuery = useDeferredValue(query);
  const [selected, setSelected] = useState<string | null>(null);
  const [view, setView] = useState<"mapa" | "lista">("mapa");
  const [here, setHere] = useState<[number, number] | null>(null);
  const [locating, setLocating] = useState(false);
  const [locateError, setLocateError] = useState<string | null>(null);
  const [baseMissing, setBaseMissing] = useState(false);
  const [coverage, setCoverage] = useState<Bounds | null>(null);

  const offers = useMemo<Offer[]>(() => {
    if (!catalog) return [];
    const result = planState.status === "ok" ? planState.result : null;
    const plans = new Map(result?.ranked.map((s, i) => [s.offer_id, { s, i }]) ?? []);
    const skipped = new Map(result?.skipped.map((s) => [s.offer_id, s.reason]) ?? []);
    return catalog
      .map((c) => {
        const found = plans.get(c.offer_id);
        return { ...c, plan: found?.s ?? null, skipped: skipped.get(c.offer_id) ?? null, rank: found?.i ?? Infinity };
      })
      .sort(compare);
  }, [catalog, planState]);

  const withPlan = planState.status === "ok";
  // La búsqueda por texto mira el título, la dirección y el lugar (municipio y provincia)
  const matching = useMemo(() => {
    const words = fold(deferredQuery).split(/\s+/).filter(Boolean);
    if (words.length === 0) return offers;
    return offers.filter((o) => {
      const hay = fold([o.title, o.address, o.place].filter(Boolean).join(" "));
      return words.every((w) => hay.includes(w));
    });
  }, [offers, deferredQuery]);
  const byType = useMemo(() => {
    const t = TYPES.find((x) => x.id === typeGroup);
    return matching.filter((o) => !t || t.types.length === 0 || t.types.includes(o.property_type ?? ""));
  }, [matching, typeGroup]);
  const shown = useMemo(
    () =>
      byType
        .filter((o) => (group === "todas" || CHANNEL[o.channel].group === group) && (!onlyPass || o.plan?.passes))
        .sort(sortBy(sort)),
    [byType, group, onlyPass, sort],
  );
  const groupCount = (g: Group) => byType.filter((o) => g === "todas" || CHANNEL[o.channel].group === g).length;
  const typeCount = (t: (typeof TYPES)[number]) =>
    matching.filter((o) => t.types.length === 0 || t.types.includes(o.property_type ?? "")).length;

  // En el mapa, solo lo ubicado y dentro de las teselas; lo demás sigue en la lista
  const onMap = useMemo(() => shown.filter(located).filter((p) => inside(coverage, p)), [shown, coverage]);
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
    // Una tesela que no llega (la red se corta, el servidor de desarrollo recompila) no rompe el
    // mapa: se queda en blanco y se vuelve a pedir al mover. Sin este manejador, MapLibre la manda a
    // console.error y en desarrollo Next la enseña como un error de la página.
    m.on("error", (e) => {
      if ((e.error as Error | undefined)?.name === "AbortError") return;
      console.warn("Mapa:", e.error?.message ?? e);
    });
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
        if (b && !inside(b, { lon: point[0], lat: point[1] })) {
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
    if (!m || !catalog || framed.current) return;
    const all = offers.filter(located).filter((p) => inside(coverage, p));
    if (all.length === 0) return; // sin ofertas en el mapa, se queda encuadrado en las teselas
    framed.current = true;
    if (all.length === 1) m.jumpTo({ center: [all[0].lon, all[0].lat], zoom: 13 });
    else {
      const bounds = new maplibregl.LngLatBounds();
      all.forEach((p) => bounds.extend([p.lon, p.lat]));
      m.fitBounds(bounds, { padding: framePadding(), maxZoom: 14, duration: still() ? 0 : 900 });
    }
    navigator.permissions
      ?.query({ name: "geolocation" as PermissionName })
      .then((p) => p.state === "granted" && locate(true))
      .catch(() => undefined);
  }, [catalog, offers, coverage, locate]);

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
        zoom: p.approximate ? Math.min(Math.max(map.current.getZoom(), 10), 12) : Math.max(map.current.getZoom(), 15),
        padding: wide ? { ...pad, left: pad.left + 440 } : { ...pad, bottom: 420 },
        duration: still() ? 0 : 800,
        essential: true,
      });
    }
  }, []);

  const chosen = offers.find((p) => p.offer_id === selected) ?? null;
  const passing = shown.filter((p) => p.plan?.passes).length;
  const auctions = shown.filter((p) => p.auction).length;
  const unlocated = shown.filter((o) => !located(o)).length;
  const outside = shown.filter(located).length - onMap.length;
  const filtered = group !== "todas" || typeGroup !== "todos" || onlyPass || query.trim() !== "";
  const hint = planHint(planState);

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
        {chosen && (
          <OfferSheet
            offer={chosen}
            note={
              !located(chosen)
                ? "Sin ubicar: no sale en el mapa."
                : chosen.approximate
                  ? "Ubicación aproximada: el punto es el centro del municipio, porque la dirección del anuncio no se ha podido situar."
                  : !inside(coverage, chosen)
                    ? "Queda fuera de la zona que cubre el mapa."
                    : null
            }
            planHint={hint}
            onClose={() => setSelected(null)}
          />
        )}
      </div>

      <aside className="map-panel" aria-label="Ofertas">
        <header className="map-panel-head">
          <h2 className="map-panel-title" aria-live="polite">
            {catalog ? (shown.length === 1 ? "1 oferta" : `${shown.length} ofertas`) : "Ofertas"}
          </h2>
          {catalog && shown.length > 0 && (
            <p className="map-panel-sub">
              {[
                auctions > 0 && (auctions === 1 ? "1 subasta" : `${auctions} subastas`),
                withPlan && (passing === 1 ? "1 encaja con tu plan" : `${passing} encajan con tu plan`),
              ]
                .filter(Boolean)
                .join(" · ")}
            </p>
          )}
        </header>

        {catalog && offers.length > 0 && (
          <div className="panel-tools">
            <label className="search-field">
              <span className="visually-hidden">Buscar por municipio, calle o provincia</span>
              <Icon name="search" small />
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Buscar municipio o calle"
                autoComplete="off"
              />
            </label>
            <label>
              <span className="visually-hidden">Ordenar</span>
              <select className="sort-select" value={sort} onChange={(e) => setSort(e.target.value as Sort)}>
                {SORTS.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        )}

        {catalog && offers.length > 0 && (
          <div className="map-filters">
            <div className="chip-row" role="group" aria-label="Cómo se vende">
              {GROUPS.map((g) => {
                const n = groupCount(g.id);
                if (g.id !== "todas" && n === 0) return null;
                return (
                  <button key={g.id} type="button" className="chip" aria-pressed={group === g.id} onClick={() => setGroup(g.id)}>
                    {g.label} <span className="chip-n">{n}</span>
                  </button>
                );
              })}
            </div>
            <div className="chip-row" role="group" aria-label="Tipo de inmueble">
              {TYPES.map((t) => {
                const n = typeCount(t);
                if (t.id !== "todos" && n === 0) return null;
                return (
                  <button key={t.id} type="button" className="chip quiet" aria-pressed={typeGroup === t.id} onClick={() => setTypeGroup(t.id)}>
                    {t.label}
                  </button>
                );
              })}
              {withPlan && (
                <button type="button" className="chip fit" aria-pressed={onlyPass} onClick={() => setOnlyPass((v) => !v)}>
                  Solo las que encajan
                </button>
              )}
            </div>
          </div>
        )}

        {hint && (
          <div className="plan-hint">
            <p>{hint.text}</p>
            {hint.href && (
              <a className="button-link primary" href={hint.href}>
                {hint.cta}
              </a>
            )}
          </div>
        )}

        <div className="map-panel-body">
          {!catalog && !catalogError && <Skeleton label="Cargando las ofertas…" shape="text" />}
          {catalogError && <p className="failure">{catalogError}</p>}

          {catalog && shown.length === 0 && (
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
                    setGroup("todas");
                    setTypeGroup("todos");
                    setOnlyPass(false);
                    setQuery("");
                  }}
                >
                  Quitar los filtros
                </button>
              ) : (
                <AppLink className="button-link primary" href="/ofertas">
                  Añadir un anuncio
                </AppLink>
              )}
            </div>
          )}

          <ol className="listings">
            {shown.map((o) => (
              <li key={o.offer_id}>
                <Listing offer={o} current={o.offer_id === selected} onSelect={select} />
              </li>
            ))}
          </ol>
        </div>

        <footer className="map-panel-foot">
          {(unlocated > 0 || outside > 0) && (
            <span className="hint">
              {[unlocated > 0 && `${unlocated} sin ubicar`, outside > 0 && `${outside} fuera del mapa`].filter(Boolean).join(" · ")}
            </span>
          )}
          <AppLink className="map-add" href="/ofertas">
            <svg viewBox="0 0 20 20" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
              <path d="M10 4v12M4 10h12" />
            </svg>
            Añadir un anuncio
          </AppLink>
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

function Listing({ offer: o, current, onSelect }: { offer: Offer; current: boolean; onSelect: (id: string) => void }) {
  const cash = fig(o.plan, "cashflow.monthly_after_tax");
  const when = ending(o);
  return (
    <button type="button" className="listing" style={channelStyle(o.channel)} aria-current={current} onClick={() => onSelect(o.offer_id)}>
      <OfferPhoto offerId={o.offer_id} kinds={o.photos} images={o.images} propertyType={o.property_type} className="listing-photo" />
      <span className="listing-body">
        <span className="listing-top">
          <span className="ch-badge">{CHANNEL[o.channel].label}</span>
          {o.status === "por_confirmar" && <span className="map-tag quiet">Por confirmar</span>}
          {when && <span className="listing-when">{when}</span>}
        </span>
        <span className="listing-title">{o.title}</span>
        {(o.address || o.place) && (
          <span className="listing-place">
            {o.approximate && <span title="Ubicación aproximada">≈ </span>}
            {o.address ?? o.place}
          </span>
        )}
        <span className="listing-price">
          {o.price ? (
            <>
              <strong>{formatValue(o.price, "EUR")}</strong>
              <small>{o.price_kind === "valor_subasta" ? "valor de subasta" : "precio"}</small>
            </>
          ) : (
            <small>Sin precio en el anuncio</small>
          )}
          {o.built_area_m2 && <small className="listing-area">{formatArea(o.built_area_m2)}</small>}
        </span>
        {o.plan ? (
          <span className={`listing-fit ${o.plan.passes ? "pass" : "fail"}`}>
            <span className={o.plan.passes ? "status pass" : "status fail"}>{o.plan.passes ? "Encaja" : "No encaja"}</span>
            {cash && (
              <strong>
                <Amount text={formatValue(cash.value, cash.unit)} />
              </strong>
            )}
          </span>
        ) : o.skipped ? (
          <span className="listing-fit none">Sin plan: {o.skipped.replace(/\.$/, "").toLowerCase()}</span>
        ) : null}
      </span>
    </button>
  );
}

function OfferSheet({
  offer: o,
  note,
  planHint: hint,
  onClose,
}: {
  offer: Offer;
  note: string | null;
  planHint: ReturnType<typeof planHint>;
  onClose: () => void;
}) {
  const close = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    close.current?.focus({ preventScroll: true });
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [o.offer_id, onClose]);

  const facts: [string, string][] = [];
  if (o.price) facts.push([o.price_kind === "valor_subasta" ? "Valor de subasta" : "Precio", formatValue(o.price, "EUR")]);
  if (o.deposit) facts.push(["Depósito para pujar", formatValue(o.deposit, "EUR")]);
  if (o.built_area_m2) facts.push(["Superficie construida", formatArea(o.built_area_m2)]);
  const when = ending(o);
  if (when) facts.push([o.channel === "venta_directa" ? "Plazo" : "Subasta", when]);
  else if (o.auction_state) facts.push(["Subasta", o.auction_state]);
  if (o.possession) facts.push(["Posesión", o.possession]);
  if (o.habitual_residence !== null && o.habitual_residence !== undefined)
    facts.push(["Vivienda habitual del deudor", o.habitual_residence ? "Sí" : "No"]);

  const verdict = [
    ["cashflow.monthly_after_tax", "Tu cash flow"],
    ["irr.rate", "TIR"],
    ["cashflow.cash_invested", "Lo que pones"],
  ] as const;

  return (
    <section className="offer-sheet" style={channelStyle(o.channel)} aria-labelledby="ficha-titulo">
      <div className="sheet-media">
        <OfferPhoto offerId={o.offer_id} kinds={o.photos} images={o.images} propertyType={o.property_type} credit className="sheet-photo" />
        <button ref={close} type="button" className="sheet-close" onClick={onClose} aria-label="Cerrar la ficha">
          <svg viewBox="0 0 20 20" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
            <path d="M5 5l10 10M15 5 5 15" />
          </svg>
        </button>
      </div>
      <div className="sheet-body">
        <div className="listing-top">
          <span className="ch-badge">{CHANNEL[o.channel].label}</span>
          {o.status === "por_confirmar" && <span className="map-tag quiet">Por confirmar</span>}
        </div>
        <h2 id="ficha-titulo">{o.title}</h2>
        {(o.address || o.place) && (
          <p className="sheet-address">
            {o.address ?? o.place}
            {o.address && o.place && <span>{o.place}</span>}
          </p>
        )}

        {facts.length > 0 && (
          <dl className="sheet-facts">
            {facts.map(([k, v]) => (
              <div key={k}>
                <dt>{k}</dt>
                <dd>{v}</dd>
              </div>
            ))}
          </dl>
        )}

        {o.plan ? (
          <div className={`sheet-verdict ${o.plan.passes ? "pass" : "fail"}`}>
            <span className={o.plan.passes ? "status pass" : "status fail"}>
              {o.plan.passes ? "Encaja con tu plan" : "No encaja con tu plan"}
            </span>
            <div className="offer-sheet-figures">
              {verdict.map(([key, label]) => {
                const f = fig(o.plan, key);
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
            {o.plan.reasons.length > 0 && <p className="verdict-reason">{o.plan.reasons.join(". ")}.</p>}
          </div>
        ) : o.skipped ? (
          <p className="sheet-noplan">No se puede calcular tu plan: {o.skipped.replace(/\.$/, "").toLowerCase()}.</p>
        ) : hint ? (
          <p className="sheet-noplan">{hint.text}</p>
        ) : null}

        {o.corrected && <p className="sheet-warning">El BOE publicó una corrección de este anuncio: compruébala en la fuente antes de pujar.</p>}
        {note && <p className="hint">{note}</p>}

        <div className="verdict-actions">
          <AppLink className="button-link primary" href={`/oferta/${o.offer_id}`} data={DATA.offer(o.offer_id)}>
            Ver la ficha
          </AppLink>
          {o.plan && (
            <AppLink className="button-link" href={`/plan/${o.offer_id}`} data={DATA.plan(o.offer_id)}>
              Ver mi plan
            </AppLink>
          )}
          {o.status === "por_confirmar" && (
            <AppLink className="button-link" href={`/ofertas?id=${o.offer_id}`}>
              Confirmar los datos
            </AppLink>
          )}
          {o.source_url && (
            <a href={o.source_url} target="_blank" rel="noreferrer">
              Ver en {o.source_name === "Tu anuncio" ? "el anuncio" : o.source_name}
            </a>
          )}
        </div>
      </div>
    </section>
  );
}
