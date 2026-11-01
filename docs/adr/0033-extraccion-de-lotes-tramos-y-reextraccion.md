# ADR-0033: Extracción de lotes: tramos por encabezados, citas compuestas y nueva extracción

**Estado:** Aceptada · **Fecha:** 2026-11-01 · **Decide:** Rodrigo (pide cerrar los lotes que se
quedan sin dirección ni referencia)

## Contexto
De 62 lotes extraídos de la sección V, 32 no tenían ni dirección ni referencia catastral y no se
podían ubicar. Ninguno faltaba porque el anuncio no los diera: la comprobación de citas (ADR-0013,
ADR-0014) había rechazado lo que propuso el modelo (qwen3:14b), por tres causas:

1. **Sin tramo (22 lotes).** El tramo de cada lote empieza en la cita de su etiqueta. El modelo la
   parafraseaba («El texto original menciona 'Finca 1'…») o daba un valor que no casaba con la
   cita («Lote 2» por «Lote nº 2.-»): sin etiqueta no hay tramo y se pierden todos los campos.
2. **Dirección compuesta.** El modelo junta trozos de la cita: «Plaza Cuartel 6, Cacín» de «en
   CACÍN (Granada), Plaza Cuartel, 6». La comprobación pedía el valor entero como texto seguido.
3. **Referencias con espacios o barras.** «21026A0 0400061 0000» (18 caracteres, sin los de
   control) o «2006983/9728140/0439/9E» (Gipuzkoa) no pasaban el formato de 14 o 20.

Además, volver a extraer un anuncio no cambiaba sus lotes: `upsert_offer` solo actualiza el título
y lo recibido. Y lo que proponía el modelo no se guardaba: una regla de comprobación mejor no se
podía aplicar sin volver a pasar por el LLM.

Los anuncios marcan cada lote al principio de un párrafo, con formas regulares: «Lote nº 2.-»,
«LOTE ÚNICO», «Lote 2 –», «Finca 1:», «1.», «1.1», «Uno)».

## Decisión
1. **Encabezados del documento.** Los párrafos que empiezan por un encabezado de lote marcan dónde
   acaba un tramo: el de un lote con etiqueta va de su etiqueta al siguiente lote o al siguiente
   encabezado, lo que llegue antes. Así un lote sin etiqueta en medio no queda dentro del tramo
   del anterior.
2. **Tramo de reserva.** Si la etiqueta no vale, el tramo del lote es el del encabezado en el que
   caen **todas** sus citas de ubicación (dirección, referencia, municipio) que están en el
   documento. Si caen en tramos distintos, o dos lotes dan el mismo, no hay tramo. Los demás campos
   se comprueban contra ese tramo como siempre: una cita de otro lote se rechaza.
3. **Texto compuesto.** Cada parte del valor separada por comas tiene que estar en la cita como
   palabras seguidas, sin contar mayúsculas, tildes ni signos. Ninguna palabra queda fuera.
4. **Referencias.** Se comparan sin espacios, puntos, guiones ni barras; valen de 8 a 20
   caracteres con al menos cinco cifras (la Dirección General y los catastros forales, ADR-0032).
   El formato de cada servicio lo comprueba el localizador.
5. **Instrucciones al modelo:** la etiqueta es el encabezado copiado; `evidence` nunca es una frase
   suya; la dirección se copia como está escrita y el municipio y la provincia van aparte.
6. **Lo que propone el modelo se guarda** en el anuncio (`extracted.proposed`). `extract_offers`
   con `{"recheck": true}` vuelve a comprobarlo sin el LLM.
7. **Una extracción nueva** de un anuncio actualiza sus lotes sin confirmar (si cambia lo que los
   ubica, se vuelven a ubicar) y retira los que ya no encuentra: `retirada` (migración 0019), sin
   inmueble y con el motivo; no se borran. Un lote confirmado no se toca.

Nada de esto deja pasar una cifra o un texto que no esté en la fuente: cada valor sigue saliendo
de una cita literal que está en el tramo de su lote.

## Opciones consideradas
- **Una llamada al modelo por lote**, con el tramo cortado de antemano: más llamadas (un anuncio
  de doce lotes, doce) y la división del documento seguiría dependiendo de los encabezados. Se
  deja para si el tramo de reserva no basta.
- **Aceptar la etiqueta por su número** («Lote 4» para «Lote nº 4:»): el número suelto también
  está en otros sitios («parcela 4»); las citas de ubicación son una señal más fuerte.

## Consecuencias
- Medido con el banco de F6.9 ampliado con seis anuncios reales (`data/evaluation/`): ver
  `docs/research/f4-extraccion-lotes.md`.
- Las reglas nuevas se aplican a lo ya extraído con `recheck` solo si el anuncio guardó lo que
  propuso el modelo; los anteriores a este cambio se vuelven a extraer una vez.
