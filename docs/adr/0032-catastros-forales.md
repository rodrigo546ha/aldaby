# ADR-0032: Parcelas de los catastros forales (País Vasco y Navarra)

**Estado:** Aceptada; condiciones de reutilización por verificar por Rodrigo · **Fecha:** 2026-11-01
· **Decide:** Rodrigo (pide buscar estos servicios tras ADR-0031)

## Contexto
La Dirección General del Catastro no cubre el País Vasco ni Navarra: cada diputación foral y el
Gobierno de Navarra llevan su propio catastro. El lote BOE-B-2026-34912#1 (FOGASA, un pabellón en
Azpeitia, Gipuzkoa) trae la referencia `2001860840226144403E`, que `Consulta_CPMRC` no conoce, y
ninguna dirección: se quedaba sin ubicar.

Los cuatro publican sus parcelas como servicios WFS (INSPIRE en el País Vasco), comprobados con
peticiones reales el 2026-11-01:

| Territorio | Servicio | Identificador de la parcela | Punto |
| --- | --- | --- | --- |
| Gipuzkoa (20) | `b5m.gipuzkoa.eus/inspire/wfs/gipuzkoa_wfs_cp`, `cp:CadastralParcel` | `nationalCadastralReference` de 7 cifras en urbana (`6084022`); `localId` `018-6084022-…` con el municipio INE delante | `referencePoint`, EPSG:4258 (lat, lon) |
| Bizkaia (48) | `geo.bizkaia.eus/arcgisserverinspire/…/InspireFeatureDownload/service`, `cp:CadastralParcel` | `48.001.1055.99082` | `referencePoint`, EPSG:4258 (lat, lon) |
| Álava (01) | `geo.araba.eus/geoserver/INSPIRE_CP/wfs`, `INSPIRE_CP:CP.CadastralParcel` | 8 cifras (`64010007`) | `referencePoint`; pedido en EPSG:4258 (lon, lat) |
| Navarra (31) | IDENA, `idena.navarra.es/ogc/wfs`, `CATAST_Pol_ParcelaRusti`, `…Urba`, `…Mixta` | municipio (`CMUNICIPIO`, las tres últimas cifras del código INE), polígono y parcela | sin punto: se calcula uno dentro del polígono |

- **Gipuzkoa:** la referencia del lote se lee como provincia (20), municipio (018, Azpeitia, INE
  20018) y parcela (`6084022`), seguida de la unidad. El servicio la encuentra: 39.829 m² en
  (43.2103, −2.2543), junto al barrio de Lasao, como dice el anuncio («complejo industrial… en
  las proximidades del barrio de Lasao»). Cada parcela trae sus versiones (`beginLifespanVersion`,
  `endLifespanVersion`): vale la que no tiene fin.
- **Condiciones:** Gipuzkoa permite reutilizar «freely… under the following terms: 1. Authorship
  must be indicated»; IDENA, CC BY 4.0 citando la fuente; Bizkaia y Álava declaran `Fees` y
  `AccessConstraints` vacíos («None», «NONE»). Por verificar en sus avisos legales.
- **`robots.txt`:** `b5m.gipuzkoa.eus` y `geo.bizkaia.eus` no tienen (404); el de `geo.araba.eus`
  solo veta rutas del portal (`/c`, `/*/search`…); el de `idena.navarra.es` veta `/ogc/wms`, no
  `/ogc/wfs`.

## Decisión
1. **Provincia foral, catastro foral.** Si la oferta es de Álava, Bizkaia, Gipuzkoa o Navarra (por
   su provincia o por la forma de la referencia), no se pregunta a la Dirección General del
   Catastro: se pregunta al servicio de su territorio.
2. **Solo formatos comprobados:**
   - Gipuzkoa: referencia `20` + municipio (3) + parcela (7) + resto → parcela con ese número y
     `localId` de ese municipio.
   - Bizkaia: `48.MMM.PPPP.NNNNN` (con o sin puntos) → `nationalCadastralReference` exacta.
   - Álava: 8 cifras → `nationalCadastralReference` exacta.
   - Navarra: polígono y parcela del texto (como en ADR-0031) y municipio de la oferta, cuyo código
     INE da `candidates` de CartoCiudad dentro de la provincia 31.
   El polígono y parcela de Gipuzkoa, Bizkaia y Álava no se usan: el formato de sus referencias
   rústicas no está comprobado.
3. **Las mismas comprobaciones:** el punto tiene que caer en una sección cargada y en el municipio
   de la oferta (por el nombre o por su código INE, ADR-0031). Si el servicio no responde, se
   reintenta (ADR-0031).
4. **Caché** en `geocode_cache` (`foral:<provincia>:<referencia>`, un año), con la fuente de cada
   servicio en `sources`.

## Opciones consideradas
- **Descargar las parcelas (ATOM) de cada territorio:** ubicaría sin consultar fuera, pero son
  conjuntos grandes y cambian; con muy pocos lotes forales, la consulta puntual basta.
- **Consulta del Registro de la Riqueza Territorial de Navarra** (`catastro.navarra.es`): es una
  web para personas; IDENA publica las mismas parcelas como servicio.

## Consecuencias
- Los lotes de Gipuzkoa con referencia, de Bizkaia y Álava con su referencia exacta y de Navarra
  con polígono y parcela se ubican con el catastro que les corresponde.
- Cuatro fuentes nuevas en `docs/DATA_SOURCES.md`, con su cita.
