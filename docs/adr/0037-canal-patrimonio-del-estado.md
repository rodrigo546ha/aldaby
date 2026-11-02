# ADR-0037: Canal del Patrimonio del Estado: ventas directas

**Estado:** Aceptada · **Fecha:** 2026-11-02 · **Decide:** Rodrigo («Sí, los canales», tras
`docs/research/fuentes-utilizables.md`)

## Contexto
La Dirección General del Patrimonio del Estado publica tres RSS:
- subastas y concursos (`RssSubastas.aspx?hiloId=12`);
- ventas directas (`RssVentasDirectas.aspx?hiloId=15`);
- abintestatos (`RssAbintestatos.aspx?hiloId=13`).

Cada elemento enlaza a una ficha con:
- la delegación y la denominación;
- el tipo de procedimiento y la naturaleza de los bienes;
- las fechas y, a veces, la superficie, el precio y la fianza;
- la documentación en PDF: pliego, anexos, una hoja por lote o la lista de lotes desiertos.

**Licencia (comprobado el 2026-11-02):** el aviso legal de Hacienda permite «la reutilización de
los documentos sometidos a ellas para fines comerciales y no comerciales», con dos condiciones:
- citar «Origen de los datos: Ministerio de Hacienda» y la fecha de actualización;
- no desnaturalizar el sentido.

El `robots.txt` de `www.hacienda.gob.es` solo prohíbe `/RRHH/` y algunos PDF concretos.

**Lo que ya teníamos:** el 2026-11-02 el RSS de subastas tenía 8 elementos.
- 7 ya estaban en `boe_seccion_v`: Soria, Valencia, Granada, Lugo, Ciudad Real, Zaragoza y Badajoz.
- 5 de esas 7 fichas no enlazan a su anuncio del BOE, así que la ficha no sirve para reconocerlas.
- El octavo (Madrid, subasta del 16 de diciembre) aún no había salido en el BOE.

Lo que el BOE no trae son las **ventas directas**: lotes cuya subasta quedó desierta y que se
venden por el tipo de salida durante meses. Los abintestatos anuncian el inicio de un expediente de
herencia, no una venta.

## Decisión
Canal `patrimonio_estado`, oferta pública (`org_id` nulo), con estas reglas:

1. **Solo el RSS de ventas directas.**
   - Las subastas no se leen: entran por `boe_seccion_v`. Leerlas aquí duplicaría lotes en la
     búsqueda, porque la ficha no basta para reconocer las que ya tenemos.
   - El RSS de abintestatos tampoco: no es oferta y su título lleva el nombre del fallecido.
   - Antes de cada descarga se mira el `robots.txt` de Hacienda.
2. **Cuándo se descarga una ficha.** Se identifica por su ruta bajo `/Paginas/`. Se descarga de
   nuevo solo si cambia la fecha de publicación del elemento del RSS (`pubDate`), para no bajar los
   PDF todos los días.
3. **Qué texto se extrae.** Los campos de la ficha y, si no trae superficie y precio, el texto de
   los PDF que describen lo que se vende:
   - hojas de lote (`l1-…`, «lote»);
   - listas de lotes desiertos («desierto»).

   Nunca se extraen:
   - el pliego de la subasta original, que describe también lotes que ya se vendieron;
   - los formularios: solicitud, modelo, declaración, instrucciones, calificación energética,
     planos ni calendario.
4. **Extracción:** la de los anuncios del BOE (ADR-0013, 0033, 0034). Cada línea del texto es un
   párrafo. Se quitan las líneas que se repiten en la mitad de las páginas o más (cabeceras, firma
   y código de verificación) y los números de página. Los lotes quedan `extraida`, con el tipo de
   salida como `auction_min_bid`. En una venta directa ese tipo es el precio de adjudicación.
5. **Límites:** como mucho 40 páginas y 10 MB por PDF. Un PDF que no se pueda leer o que no tenga
   texto (escaneado) se anota en el informe y la oferta se guarda sin él. No hay OCR en este canal.
6. **Cita:** la fuente (`sources`) lleva la licencia y la cita exigida. La URL de cada oferta es su
   ficha en hacienda.gob.es.

## Opciones consideradas
- **Leer también las subastas y saltar las que enlazan al BOE:** 5 de las 7 que ya teníamos no
  enlazan, así que se duplicarían. Descartado. Si una subasta del Patrimonio no llega al BOE, se
  revisa esta regla.
- **Extraer todos los PDF de la ficha:** mete lotes ya vendidos y formularios en la extracción.
  Descartado.
- **OCR de los escaneados:** pocas fichas lo necesitan. Queda para cuando aparezca alguno.

## Consecuencias
- Poco volumen: el 2026-11-02 había 5 ventas directas, todas de fincas rústicas. Sirve sobre todo
  para inversores de suelo rústico.
- La venta directa no tiene fecha de subasta: está a la venta hasta la fecha límite de la ficha.
- Las hojas de lote pueden llevar nombres de colindantes y del delegado que firma. Son textos
  públicos, como los del BOE, y se guardan igual que estos en `raw`.
