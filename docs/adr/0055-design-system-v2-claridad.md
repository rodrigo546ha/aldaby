# ADR-0055: Design system v2, «Claridad», y ficha de cada oferta

**Estado:** Aceptada · **Fecha:** 2026-11-05 · **Decide:** Rodrigo («rediseño de la UX/UI para que la
información se vea mucho mejor, más útil, legible, agradable y accesible; diseña el design system y
trabaja desde ahí»)

## Contexto
La v1 del design system (DESIGN.md, «El instrumento de profundidad») medía, con los datos de toda
España y del Portal de Subastas:
- el lienzo y los paneles a 1,20:1, y los paneles y las tarjetas a 1,15:1: no se distinguían;
- el texto atenuado sobre una tarjeta a 4,23:1, por debajo de AA;
- rótulos, botones y navegación en mayúsculas espaciadas de 10–12 px, y el cuerpo a 15 px;
- un solo color de acento para todo.

La oferta solo tenía una ficha flotante sobre el mapa. Lo que el Portal y el Catastro ya daban
(juzgado, procedimiento, hora de cierre, año de construcción, uso) no se enseñaba.

## Decisión
1. **Tokens en `apps/web/app/tokens.css`**, con nombres semánticos y contraste medido en los dos
   temas:
   - cuatro superficies que se distinguen;
   - cuatro tonos de texto, todos AA;
   - borde de control a 3:1;
   - estados de éxito, aviso, peligro e información;
   - un color por canal;
   - escala tipográfica de base 16 px, rejilla de 4, radios y una sola sombra, para lo que flota.

   Los nombres de la v1 quedan como alias, para no reescribir de golpe todo el CSS.
2. **Tipografía:** fuera las mayúsculas espaciadas, salvo en las etiquetas de 12 px. Nada por
   debajo de 13 px.
3. **Componentes nuevos** (`apps/web/app/components.css`, `components/Icon.tsx`): datos clave,
   lista de datos, aviso con icono, cronología de la subasta, panel de sección, búsqueda y orden,
   galería.
4. **Ficha de cada oferta**, `/oferta/[id]`, con `GET /offers/catalog/{id}`. Enseña:
   - fachada y vista aérea;
   - los datos que deciden en grande;
   - tu plan al lado;
   - la subasta: juzgado, procedimiento, posesión, visitas y vivienda habitual;
   - el inmueble: superficie, año y uso en el Catastro, y referencia catastral;
   - las fuentes.

   La ficha flotante del mapa lleva a ella.
5. **Lista de ofertas:** búsqueda por municipio o calle, sin tildes ni mayúsculas, y orden por
   recomendadas, acaban antes, más baratas o más caras.
6. **DESIGN.md pasa a la v2** y es la referencia para todo lo nuevo.

## Consecuencias
- El CSS de la v1 aún usa los alias (`--raised`, `--muted`…). Se pasa a los nombres nuevos al tocar
  cada pantalla.
- La ficha pide la búsqueda inversa entera para saber el plan de una oferta. Con miles de ofertas
  hará falta un endpoint del plan resumido de una sola, que no gaste un plan completo del nivel
  gratuito.
- Las fotos de fachada pueden no ser del portal exacto en un edificio con varios (ADR-0054).
