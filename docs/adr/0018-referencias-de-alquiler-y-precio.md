# ADR-0018: Referencias de alquiler y de precio, y precio estimado desde la renta

**Estado:** Aceptada (G6, F5.1–F5.4) · **Fecha:** 2026-10-30 · **Decide:** Rodrigo
Investigación: `docs/research/f5-fuentes-valoracion.md`.

## Contexto
El plan necesita la renta y el precio esperables de un inmueble con un rango honesto. Solo hay una
fuente pública de alquiler por sección censal (SERPAVI) y ninguna de precio de venta reutilizable
por debajo del municipio. Rodrigo decide estimar el precio desde la renta (2026-10-30).

## Fuentes
| Fuente | Qué se carga | Nivel | Periodo | Reutilización |
| --- | --- | --- | --- | --- |
| SERPAVI, Ministerio de Vivienda (Excel 2011–2024, 67,8 MB) | Viviendas alquiladas y mediana, P25 y P75 de €/m² mes, €/mes y m², colectiva y unifamiliar | Sección (seccionado 2021), distrito, municipio | Anual | Aviso legal del Ministerio: libre, también comercial, citando la fuente y la fecha de actualización |
| Valor tasado de la vivienda libre, Ministerio de Vivienda, en la copia de la Comunidad de Madrid (CSV) | €/m² de tasación | Municipio de más de 25.000 habitantes | Anual, 2005–2025 | CC BY 4.0 |
| INE, Índice de Precios de Vivienda, tabla 80270 (API) | Índice general, nueva y segunda mano, base 2025 | Comunidad autónoma | Trimestral | Condiciones del INE, citando la fuente |

- Se carga la provincia de Madrid (MVP), como el resto de cargadores (`PROVINCE=28`).
- **Sin dependencia nueva:** el Excel del SERPAVI se lee con la biblioteca estándar (un `.xlsx` es
  un zip con XML) en `ingestion/xlsx.py`, en streaming. El valor tasado se toma en CSV de la
  Comunidad de Madrid, que lo republica del Ministerio, en lugar del `.xls` antiguo del Ministerio,
  que pediría una biblioteca para leerlo.
- **Tabla `market_references`** en formato largo: fuente, nivel, código, año (y trimestre), medida,
  tipología, estadístico (`n`, `p25`, `mediana`, `p75`, `valor`), valor y unidad. Cada carga tiene
  su fila en `sources` con la licencia y la fecha.

## Modelo de renta (F5.3)
- Para un inmueble en la sección *s*, de tipología *t* y superficie *A*: €/m² mes de la sección
  (mediana y P25–P75) × *A*. Si la sección no tiene datos (menos de 10 alquileres), el distrito y,
  después, el municipio; la cifra dice de qué nivel sale.
- **Contracción hacia el municipio** con pocos alquileres: mediana = w·sección + (1−w)·municipio,
  w = n/(n+k). *k* es un parámetro con fecha en `data/params/` marcado PROVISIONAL hasta el
  backtesting (F5.6), no una constante.
- **Fecha de la referencia.** El último año del SERPAVI es 2024. **Actualización (2026-10-30,
  decisión de Rodrigo):** la renta se lleva al último mes publicado con el componente de alquiler
  del IPC del INE de la comunidad (tabla 76137, subgrupo 04.1, mensual, base 2025), que también
  mide los alquileres en vigor. En el backtesting, una renta de dos años pasa de quedarse corta un
  7,9 % a un 4,2 % (error mediano del 7,95 % al 4,23 %); el resto no se corrige con ningún factor
  y el aviso lo dice. El precio no usa la renta actualizada: sale de la renta y del valor tasado
  del mismo año y se actualiza con el IPV.

- **Calibración (F5.6, 2026-10-30):** el backtesting da k = 0: contraer hacia el municipio empeora
  la estimación en todos los horizontes y tamaños de sección (`docs/research/f5-6-backtesting.md`).
  El mecanismo se mantiene; el parámetro ya no es provisional.

## Precio desde la renta (F5.4)
- Relación precio/renta del municipio *m* en el año *y*: valor tasado (€/m²) / (renta mediana
  municipal del SERPAVI €/m² mes × 12).
- Precio €/m² de la sección = renta €/m² mes de la sección × 12 × relación del municipio. El rango
  sale del P25–P75 de la renta.
- Se lleva al último trimestre con el IPV de la comunidad (segunda mano o nueva según el inmueble).
- **Supuesto explícito:** la rentabilidad bruta es la misma en todo el municipio. Va en la `Figure`
  como `SourceRef(kind="assumption")`, con el modelo `SourceRef(kind="model", id="precio-renta-v1@…")`.
- Municipios sin valor tasado (menos de 25.000 habitantes): sin estimación de precio, y se dice.
- El valor tasado es tasación, no precio de compraventa; el SERPAVI son rentas declaradas, no
  ofertas. Los dos sesgos se dicen en la cifra.

## Opciones consideradas
- **Librería de modelos (scikit-learn, statsmodels):** el modelo base son cuantiles publicados y una
  contracción con un parámetro; no hace falta ninguna. Si el backtesting pide un modelo con
  variables del inmueble, ADR nuevo.
- **Notariado por código postal:** prohíbe el uso comercial. Descartado sin autorización.
- **Precio solo municipal:** sin supuestos, pero el mismo €/m² en todo Madrid capital. Descartado.
- **`.xls` del Ministerio con `xlrd`:** dependencia para un formato antiguo, teniendo el CSV.

## Consecuencias
- La renta llega a sección censal en el 72 % de las secciones de España; en las demás, el distrito
  o el municipio.
- El precio por sección hereda los límites de la renta y el supuesto de rentabilidad uniforme.
- Las tres fuentes son anuales o trimestrales: carga programada, no diaria.
