# ADR-0057: Velocidad de la navegación

- **Estado:** aceptada
- **Fecha:** 2026-11-05

## Contexto

Cambiar de pantalla tardaba demasiado:
- **Búsqueda inversa (`GET /search`):** unos 20 s. La pedían el mapa, dos veces, y la ficha de una
  oferta, que solo necesitaba el plan de esa oferta.
- **Catálogo:** 386 KB de JSON sin comprimir.
- **Plan completo:** de 2 a 7 s.
- **Enlaces internos:** eran `<a>` normales, así que cada cambio de pantalla recargaba la app entera
  y volvía a pedir todos los datos.
- **En desarrollo:** `next dev` compila cada pantalla la primera vez que se visita, de 4 a 20 s.

El perfilado (cProfile) de la búsqueda dio dos causas que no tenían que ver con el cálculo en sí:
- **`RuleBook.resolve` recorría las ~7.500 reglas en cada consulta:** son miles de reglas
  municipales de IBI y plusvalía. Hacía 825.000 comprobaciones de territorio, el 47 % del tiempo.
- **El cuadro de amortización se calculaba 1.539 veces para 46 planes:** solo había 384 distintos.

## Decisión

1. **Índice de reglas** por tipo y territorio (`RuleBook._by_kind_territory`).
   - Se consultan solo los territorios que contienen al pedido (`core.dated.containing`): España,
     comunidad, provincia y municipio.
   - Se sigue filtrando con `territory_contains`, así que el resultado es el mismo regla a regla.
   - Si alguien añade reglas a la lista, el índice se rehace.
2. **Cuadro de amortización memorizado** (`lru_cache`).
   - Es una función pura con filas inmutables.
   - Quien llama recibe su propia copia de la lista.
3. **Caché de planes por contenido** (`search.service.ContentCache`), en la memoria del proceso de
   la API.
   - **Clave:** el resumen (sha256) de todo lo que decide el plan:
     - el perfil (nunca en claro);
     - los datos de la oferta;
     - las rentas esperadas;
     - los supuestos de mercado;
     - el día;
     - la versión de las fuentes públicas cargadas (`sources`: número de filas y `fetched_at` más
       reciente);
     - las reglas y parámetros del proceso.
   - Si cambia cualquiera de esas cosas, la clave es otra y el plan se calcula de nuevo. Por
     construcción no sirve nunca un plan viejo, y no hace falta invalidarla a mano.
   - **La usan:** la búsqueda (oferta a oferta), la ficha y el plan completo (también su PDF y el
     asesor).
   - **Por qué por contenido:** `offers` no tiene marca de actualización, así que una caché por
     tiempo podría servir datos viejos.
4. **`GET /search/offers/{id}`:** el plan del usuario en una sola oferta, igual que en la búsqueda.
   Lo usa la ficha de la oferta.
5. **Respuestas comprimidas:** `GZipMiddleware` de Starlette, sin dependencias nuevas, para
   respuestas de más de 1 KB. El flujo del asesor (`text/event-stream`, ADR-0052) queda fuera por
   defecto.
6. **En la web:**
   - `lib/data.ts` guarda las respuestas mientras la app está abierta: enseña lo guardado y lo
     refresca por detrás, y si dos componentes piden lo mismo a la vez sale una sola petición.
   - `AppLink` navega con `next/link`, sin recargar, y pide los datos de la pantalla de destino al
     pasar el puntero por el enlace.
   - Al confirmar el perfil, guardar supuestos o una renta esperada, o confirmar un anuncio, se
     vacía lo que depende del plan (`invalidatePlans`).
   - Al cambiar de cliente la página se recarga entera, así que la caché empieza de cero.

## Consecuencias

Medido en este Mac, con la web en modo producción (`npm run build && npm start`):

| Medida | Antes | Ahora |
|---|---|---|
| Búsqueda, primera vez | 18–20 s | 2,6 s |
| Búsqueda, después | 18–20 s | 0,3 s |
| Plan de una oferta | 20 s | 0,2 s |
| Plan completo | 2–7 s | 0,2–0,4 s |
| Respuesta de la búsqueda | 457 KB | 27 KB comprimida |
| Respuesta del catálogo | 386 KB | 46 KB comprimido |
| Mapa con los planes | — | 0,85 s |
| Mapa → ficha | — | 82 ms |
| Ficha → plan | — | 0,38 s |
| Volver al mapa | — | 98 ms |

Límites que quedan:
- **La caché vive en la memoria de cada proceso:** se pierde al reiniciar y no se comparte entre
  procesos de la API.
- **Lo cargado a mano en una tabla de datos sin pasar por `sources`** no cambia la clave. Toda
  ingesta registra su fuente (ADR-0022); si alguna no lo hiciera, habría que reiniciar la API.
- **El modo desarrollo sigue compilando** cada pantalla la primera vez. Para usar la app con su
  velocidad real, se arranca en modo producción.
