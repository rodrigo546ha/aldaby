# ADR-0056: Simulador y perfil con el design system v2, y municipios del INE por su nombre

**Estado:** Aceptada · **Fecha:** 2026-11-05 · **Decide:** Rodrigo («Sí, rediséñalos», tras ADR-0055)

## Contexto
Tras la v2 (ADR-0055), el simulador y el perfil solo heredaban los colores y la tipografía:
- **El simulador** era un formulario de 35 campos en una columna estrecha. Pedía la comunidad y el
  municipio como códigos INE escritos a mano («ES-13», «ES-13-28079»).
- **El perfil** empezaba con un botón sin explicación. La conversación y el borrador no decían
  cuántos datos faltaban, y un error del servidor salía como «Error».

No había una tabla con los nombres de los municipios. El catálogo los sacaba del texto de cada
anuncio («MOSTOLES»).

## Decisión
1. **Relación de municipios del INE** (`data/territory/municipios.yaml`, 8.132 municipios):
   - la genera `python -m housefinder.ingestion.ine_municipios --year 2026` desde el diccionario del
     INE (`/daco/daco42/codmun/diccionarioAA.xlsx`), la misma página que la relación de provincias;
   - el `robots.txt` del INE permite `/daco/`;
   - el artículo va delante («Las Rozas de Madrid»).

   `GET /territory/municipalities?q=` busca por nombre, sin tildes ni mayúsculas, y devuelve el
   territorio de las reglas. El catálogo de ofertas usa el nombre oficial cuando la oferta está
   ubicada.
2. **Simulador por pasos** (Tú, El piso, Hipoteca, Alquiler y Venta):
   - barra de progreso y pasos con su estado (hecho, con errores);
   - en cada paso, lo obligatorio arriba y lo opcional plegado en «Más datos»;
   - campos con su unidad;
   - la comunidad, en una lista; el municipio, en un buscador accesible (combobox de WAI-ARIA);
   - al calcular con datos que faltan, un resumen enlazado lleva al paso;
   - el resultado, en un panel de veredicto que se queda fijo en escritorio.
3. **Perfil:**
   - una portada que explica los tres pasos y que los datos se guardan cifrados;
   - la entrevista como conversación, con el recuento de datos obligatorios;
   - el documento en un plegable;
   - cada dato del borrador con su origen y «Falta» si es obligatorio y está vacío;
   - «Empezar de nuevo» pide confirmación;
   - al confirmar, lleva a las ofertas.
4. **Supuestos:** rejilla de campos con unidad y explicación, y confirmación al guardar.
5. `ingestion/xlsx.iter_rows` acepta la fila de la cabecera (`header_row`).

## Consecuencias
- La relación de municipios se regenera cada año, cuando el INE publica el diccionario nuevo.
- Las respuestas de la entrevista las lee el modelo. Si tarda más de lo que espera el proxy de
  desarrollo, la web dice que se vuelva a intentar y no pierde lo escrito. La espera en sí no se
  cambia aquí.
