// MapLibre carga su worker desde una URL aparte (ADR-0051): se copia del paquete a public/ antes de
// arrancar o compilar la web, para que siempre vaya con la versión instalada. No va a git.
import { copyFileSync, mkdirSync } from "node:fs";

mkdirSync("public/mapa", { recursive: true });
copyFileSync("node_modules/maplibre-gl/dist/maplibre-gl-worker.mjs", "public/mapa/maplibre-gl-worker.mjs");
