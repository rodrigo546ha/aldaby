"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "./Motion";

// MapLibre necesita el navegador: el mapa se carga solo aquí y solo en el cliente (ADR-0051)
const OfferMap = dynamic(() => import("./OfferMap").then((m) => m.OfferMap), {
  ssr: false,
  loading: () => <Skeleton label="Cargando el mapa…" />,
});

export function MapPage() {
  return <OfferMap />;
}
