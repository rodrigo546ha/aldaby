# ADR-0053: Las subastas del Portal del BOE se guardan como lotes públicos

**Estado:** Aceptada · **Fecha:** 2026-11-04 · **Decide:** Rodrigo («Sí, arréglalos», tras la prueba de
punta a punta del Portal de Subastas)

## Contexto
ADR-0049 añadió el Portal de Subastas del BOE, pero solo bajo demanda: `/boe/subastas/*` devuelve un
JSON y no guarda nada, y `to_normalized_offers` no la llamaba nadie. Las subastas no llegaban al mapa,
a la búsqueda inversa ni al plan. La prueba del 2026-11-04 con datos reales encontró además que, si el
modelo fallaba, la extracción caía a reglas sin decirlo y daba «riesgo bajo» con cero euros de cargas.

La búsqueda inversa puntúa un lote si tiene ubicación, tipo de inmueble «vivienda», precio y superficie
construida. El Portal no publica la superficie.

## Decisión
1. **Canal `boe_subasta_portal`** (`offers/channels/subastas_portal.py`), con un trabajo diario
   (`offers_boe_portal`, 09:25). Busca las subastas de inmuebles de la provincia (Madrid, `28`)
   celebrándose y en próxima apertura, en una página de hasta 500. Descarga las pestañas solo de las
   nuevas o de las que cambian de estado o de fecha de conclusión, con una pausa de un segundo entre
   subastas y un máximo de 100 por ejecución. La primera carga de Madrid son unas 70.
2. **Cada lote es una oferta pública de tipo `lote`** (sin organización), como los del BOE sección V:
   sin precio pedido (`asking_price` nulo, lo que la marca como subasta en el plan) y con el valor de
   subasta como tipo (`auction_min_bid`), que es lo que usa el simulador de puja (ADR-0047). La puja
   mínima del Portal es un mínimo de puja, no el tipo. También se guardan el depósito, la dirección, la
   referencia catastral y, en `extracted`, el tipo de inmueble (de «Inmueble (Vivienda)», etc.) y los
   datos del Portal que no son cifras del plan (estado, conclusión, vivienda habitual, posesión).
3. **Superficie y uso del Catastro.** Con una referencia de 20 caracteres, `Consulta_DNPRC` del mismo
   servicio de la Sede Electrónica del Catastro que ya usa ADR-0016 da la superficie construida
   (`sfc`) y el uso (`luso`). Se pide al descargar la subasta y se guarda en lo recibido. Sin
   referencia, el lote se guarda y se ubica por su dirección, pero la búsqueda lo deja fuera con su
   motivo («Falta la superficie construida»). Leer la superficie de la certificación registral con el
   modelo queda para más adelante.
4. **Los documentos y la extracción con IA no entran en el trabajo diario**: con el modelo local cuesta
   minutos por subasta. Siguen bajo demanda (`/boe/subastas/scrape`).
5. **El riesgo de una subasta lo decide el código**, no el modelo (enmienda a ADR-0049): «alto» con una
   carga previa comprobada o el inmueble ocupado; «sin_evaluar» si la certificación de cargas no la ha
   leído el modelo; «bajo» solo con la certificación leída, la carga ejecutada citada y el inmueble
   libre; «medio» en lo demás. El informe dice si los documentos los leyó el modelo o las reglas y por
   qué. El texto que va al modelo se recorta a 24.000 caracteres, la certificación primero, para que
   quepa en una ventana de 16.384 tokens. El resumen del modelo se descarta si lleva números.

## Consecuencias
- Las subastas con referencia catastral completa aparecen en el mapa y en el plan, con su simulador
  de puja. Las demás se ven en la lista de descartadas con el motivo.
- La lista de subastas del Portal y la de avisos de la sección IV (ADR-0017) pueden traer la misma
  subasta: son canales distintos y no se deduplican entre sí por ahora (el inmueble sí, por referencia
  catastral o cercanía, al ubicarlo).

## Enmienda (2026-11-05): Ámbito nacional (toda España) y paginación
- **Ámbito nacional por defecto:** La búsqueda en el Portal (`subastas_ava.php`) y en la ingesta
  diaria (`offers_boe_portal`) utiliza por defecto `province=""` (`-- Todas --` en el formulario del BOE),
  cubriendo las 52 provincias españolas en lugar de limitarse a Madrid (`28`).
- **Paginación multi-página:** Se añade soporte para seguir la paginación (`subastas_ava.php?accion=Mas`)
  mediante el parámetro `max_pages` (por defecto 5 páginas de 500 resultados en el canal diario),
  permitiendo indexar las ~900+ subastas activas simultáneas en España.
- **Avisos de la sección IV del BOE:** El canal `boe_subastas` incorpora el parámetro `all_spain=True`
  para consultar las sedes judiciales de toda España sin restringirse a las 21 de Madrid ni al
  territorio `ES-13`.
