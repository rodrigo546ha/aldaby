# ADR-0016: Ubicación de ofertas por referencia catastral (Catastro)

**Estado:** Aceptada; condiciones de reutilización por verificar por Rodrigo · **Fecha:** 2026-10-29 ·
**Decide:** Rodrigo

## Contexto
Las ofertas se ubican por dirección con CartoCiudad (ADR-0009). En la prueba de F4.1 (ADR-0015),
CartoCiudad llevó «Carretera M-119 21, Alcalá de Henares» a una calle de Murcia. Muchos anuncios
del BOE no traen una dirección geocodificable («porción de terreno situado en la Carretera
M-119…»), pero sí la referencia catastral, que identifica la parcela sin ambigüedad.

## Decisión
- **Fuente:** el servicio de coordenadas de la Sede Electrónica del Catastro,
  `Consulta_CPMRC` («consulta de coordenadas por Provincia, Municipio y Referencia Catastral»),
  en su versión WCF con salida JSON:
  `https://ovc.catastro.meh.es/OVCServWeb/OVCWcfCallejero/COVCCoordenadas.svc/json/Consulta_CPMRC?SRS=EPSG:4326&RefCat=<14 caracteres>`.
  - Es un servicio de «información catastral no protegida y que por tanto pueden ser accedidos por
    cualquier ciudadano» (Servicios web libres de la Sede Electrónica del Catastro, v2.6, §1). No
    pide registro ni clave.
  - Se usa la versión WCF, no la ASMX: los servicios libres se migraron a WCF en la v2.0 del
    documento (27-10-2022) y la página de servicios web avisa de que los ASMX «dejarán de estar
    operativos».
  - Devuelve el centroide de la parcela (`xcen`, `ycen`), el sistema de referencia y la dirección
    catastral (`ldt`); los errores llegan en `lerr` con `cod` y `des` (Anexo I).
- **Solo los 14 primeros caracteres** (la parcela): es lo que pide el servicio. Un edificio con
  varios pisos comparte parcela; el inmueble concreto lo distingue la deduplicación por referencia
  completa y superficie (F4.6).
- **Orden del localizador** (`offers/locate.py`): primero la referencia catastral; si no la hay o
  el Catastro no la encuentra, la dirección con CartoCiudad. En los dos casos el punto tiene que
  caer en una sección censal cargada y, si la oferta dice su municipio, la dirección encontrada
  tiene que ser de ese municipio.
- **Caché:** la misma tabla `geocode_cache` (consulta `rc:<14 caracteres>`, un año), con su fila en
  `sources` (`catastro-coordenadas`).
- **Petición:** `User-Agent` de HouseFinder, una consulta por referencia nueva, sin reintentos en
  bucle; los fallos dejan la oferta sin ubicar.

## Condiciones de uso
- Aviso legal de la Sede: «Se autoriza la reproducción total o parcial de los contenidos del
  Portal, siempre que se cite expresamente su origen.» Cita: «Fuente: Dirección General del
  Catastro».
- **Por verificar (Rodrigo):** la normativa de la página de servicios web
  (`https://www.catastro.hacienda.gob.es/ayuda/normativasec.htm`), que no se ha leído, y si hay
  límites de uso o condiciones para un uso comercial. Hasta entonces, la fuente queda registrada
  con esta cita y el estado «por verificar».

## Opciones consideradas
- **Solo CartoCiudad:** falla con direcciones rurales o mal escritas. Insuficiente.
- **Cartografía catastral INSPIRE (descarga de parcelas por municipio):** permite ubicar sin
  consultar fuera, pero es un conjunto de datos grande y una descarga nueva. Para el volumen actual
  (unas pocas ofertas al día), la consulta puntual basta.
- **`Consulta_DNPRC`** (datos no protegidos del inmueble): da superficie, uso y año, útiles para
  confirmar una oferta, pero no coordenadas. Queda para más adelante.

## Consecuencias
- Las ofertas con referencia catastral se ubican aunque su dirección no sirva.
- Nueva fuente externa en `docs/DATA_SOURCES.md`, con la cita «Fuente: Dirección General del
  Catastro» donde se muestre una ubicación que salga de ella.
