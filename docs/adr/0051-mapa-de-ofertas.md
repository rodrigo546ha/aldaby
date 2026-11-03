# ADR-0051: Mapa de ofertas con teselas propias de OpenStreetMap

**Estado:** Aceptada · **Fecha:** 2026-11-04 · **Decide:** Rodrigo («OSM propio en PMTiles», «en tus
ofertas + botón», docs/PROPUESTA_UX.md U5)

## Contexto
Rodrigo quiere ver las ofertas en un mapa que empiece donde está el usuario. La búsqueda inversa ya lee
el punto de cada inmueble (`db/offers.py`, `_CANDIDATES`) pero no lo devuelve. La regla de oro 3 excluye
proveedores comerciales de datos, así que Mapbox, MapTiler, Google o Stadia quedan fuera.

Opciones leídas el 2026-11-04:
- **tile.openstreetmap.org:** su política (operations.osmfoundation.org/policies/tiles) da servicio «best
  effort», sin SLA, y puede bloquear el uso intensivo sin aviso. No sirve para producción.
- **IGN, «Mapa Ciudadano» vectorial (vt-mapabase.idee.es):** oficial, gratuito y con estilo editable, pero
  sin licencia concreta escrita para el servicio y con una URL «provisional».
- **IGN-Base WMTS:** CC BY 4.0 («CC BY 4.0 scne.es» al pie), pero raster ya pintado: no admite el tema
  oscuro ni la paleta de Aldaby.
- **PMTiles de Protomaps:** extracto de OpenStreetMap como «ODbL Produced Work», con atribución a
  OpenStreetMap obligatoria; un solo fichero que se sirve con peticiones HTTP Range. Su documentación
  desaconseja enlazar sus builds y pide copiarlos al almacenamiento propio. Ni `build.protomaps.com` ni
  `protomaps.github.io` publican `robots.txt` (404).

## Decisión
1. **Teselas propias:** un extracto de OpenStreetMap en `teselas.pmtiles`, sacado una vez de un build de
   Protomaps con `pmtiles extract` (`make mapa`). En local, de la Comunidad de Madrid hasta zoom 15; en el
   servidor, de España cuando haga falta. El fichero no entra en git ni en la imagen de la web
   (`.gitignore`, `.dockerignore`): en local lo sirve Next desde `public/mapa/` y en el servidor, Caddy
   desde un volumen, siempre en `/mapa/teselas.pmtiles`.
2. **Letras del estilo propias:** los glifos de Noto Sans (OFL) en `public/mapa/fonts/`, solo los rangos que
   usan los nombres en español. Sin iconos de puntos de interés. Así ninguna petición del mapa sale a un
   tercero.
3. **Librerías:** MapLibre GL JS 6.15.0, `pmtiles` 4.5.0 y `@protomaps/basemaps` 5.7.2 para las capas del
   estilo (todas BSD-3-Clause), con versión exacta y de más de dos semanas. MapLibre se carga solo en la
   página del mapa.
4. **Estilo:** las capas de Protomaps con los colores de Aldaby en los dos temas (verde portal en oscuro,
   arena en claro). La atribución «© OpenStreetMap» va siempre visible en el mapa.
5. **Datos:** `ScoredOut` lleva `lon`, `lat` y `location_source` (Catastro, CartoCiudad, catastro foral o el
   propio canal). La web pinta lo que devuelve la búsqueda y no calcula nada (regla de oro 1).
   Mientras las ofertas sean cientos, la búsqueda entera va en una petición y el mapa agrupa los puntos en
   el navegador; con miles hará falta pedir por caja y agrupar en el servidor.
6. **Ubicación del usuario:** el mapa abre encuadrando las ofertas. El botón «Centrar en mí» pide
   `navigator.geolocation` y, si el permiso ya estaba concedido, centra solo. La posición no sale del
   navegador: ni a la API ni a la analítica.

## Alternativas descartadas
- Las tres primeras opciones del contexto, por los motivos dichos.
- **Leaflet con teselas raster:** no admite estilo propio con teselas vectoriales sin plugins.

## Consecuencias
- En el servidor hace falta subir el extracto de España (varios GB) al volumen del mapa y añadir la ruta a
  Caddy. Mientras no esté, el mapa enseña las ofertas sobre un fondo liso con un aviso.
- Actualizar el mapa base es repetir `make mapa` con un build más reciente.
