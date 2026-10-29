# F4 · Cuánta oferta de vivienda en Madrid trae la sección V del BOE

**Fecha:** 2026-10-29 · **Datos:** sumarios reales del BOE del 30/09/2026 al 29/10/2026 (26 días con
BOE), los mismos que sirvieron para calibrar la vigilancia (F2.6). Sin descargas nuevas.

## Método
- Disposiciones de la sección V (anuncios) cuyo título encaja con el filtro de `ingestion/boe.py`
  (subasta, enajenación o venta + inmueble, vivienda, finca, local o piso).
- De ellas, las que nombran Madrid o un municipio grande de la Comunidad en el título o el
  departamento.

## Resultado

| | Anuncios |
| --- | --- |
| Venta o subasta de inmuebles, toda España | 31 (≈ 1,2 al día) |
| Hacienda | 15 |
| Seguridad Social (TGSS) | 10 |
| Otros ministerios | 6 |
| **Con Madrid en el título o el departamento** | **1** (TGSS de Madrid, 28/10/2026) |

Límite del método: los anuncios de Hacienda pueden incluir lotes de Madrid que el título no nombra;
para saberlo hay que leer el texto de cada anuncio. Aun así, el orden de magnitud es de unos pocos
anuncios al mes para Madrid, y cada uno con pocos lotes de vivienda.

## Consecuencia para F4
- La sección V no basta para el criterio de salida («cada día entran ofertas nuevas de al menos dos
  canales»). Sirve como canal complementario y barato: el sumario ya se lee cada día.
- El volumen de Madrid está en el **Portal de Subastas del BOE** (judiciales y de la Agencia
  Tributaria) y en los **servicers**. Los dos dependen de condiciones de uso por revisar (F4.3 con ADR,
  F4.5 con la consulta legal de F0.6).
- El **enlace pegado** (F4.1) no da oferta diaria, pero es el canal con más valor por usuario.
