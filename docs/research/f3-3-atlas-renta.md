# F3.3 · Atlas de Distribución de Renta de los Hogares (ADRH) por sección censal

**Fecha:** 2026-10-29 · **Estado:** investigación; nada descargado todavía.

## Qué publica el INE para la provincia de Madrid

Serie 2015–2024 (edición de octubre de 2026), en
[INEbase](https://www.ine.es/dynt3/inebase/index.htm?padre=12385&capsel=5690). Diez tablas por
provincia; cada una con 5.011 unidades territoriales (179 municipios, sus distritos y 4.586
secciones) y diez años:

| Tabla | Contenido | Indicadores |
| --- | --- | --- |
| 31097 | Renta media y mediana | renta neta media por persona y por hogar, media y mediana por unidad de consumo, renta bruta media por persona y por hogar (6) |
| 31105 | Indicadores demográficos | edad media, % menores de 18, % de 65 y más, tamaño medio del hogar, % hogares unipersonales, población, % población española (7) |
| 37727 | Desigualdad | índice de Gini, P80/P20 (2) |
| 31098 | Fuentes de ingresos | (no necesaria para el MVP) |
| 31099–31104 | % de población bajo umbrales de renta | (no necesarias para el MVP) |

Cada serie trae en sus metadatos el código INE de 10 cifras de la sección (API Tempus del INE,
`SERIES_TABLA` con `det=2`), así que no hace falta deducirlo del nombre.

## Con qué cartografía se cruza cada año

- **Metodología** ([metodologia_adrh.pdf](https://www.ine.es/metodologia/metodologia_adrh.pdf),
  apartados 2.1 y 2.3): la renta es la del IRPF de un año natural y la población, la del Censo
  Anual a 1 de enero del año siguiente, que sitúa a cada residente en su sección.
- **Conclusión (inferida, no escrita así en la metodología):** la renta del año t va sobre el
  seccionado a 1 de enero de t+1, que es la capa `Secciones_<t+1>` del INE. La renta de 2024 cuadra
  con la cartografía de 2025 que ya está cargada.
- **Comprobación con los datos:** de las 4.586 secciones del ADRH de Madrid, las 4.518 de la
  cartografía de 2025 están todas; las otras 68 son códigos de años anteriores que ya no existen.
  Es lo esperable si cada año usa su propio seccionado.
- **Consecuencia:** para series (tendencias) hay que cruzar cada año con su cartografía t+1. Unir un
  valor de 2016 a un polígono de 2025 solo por el código puede ser falso si la sección cambió.

## Avisos de la metodología que deben llegar al usuario

- La renta se refiere a la «población encontrada» en el IRPF, no a todos los residentes (apartado 3.3).
- Desde 2020, una sección o distrito con menos de 100 habitantes recibe la renta media del
  distrito o municipio que la contiene: su valor no es propio.
- Gini, P80/P20 y fuentes de ingresos solo se publican con al menos 100 residentes.
- Desde la edición 2023 la población sale del Censo Anual de Población y no del Fichero Precensal:
  puede haber saltos bruscos de población entre años en algunas secciones.

## Licencia

Datos del INE: CC BY 4.0 según su [aviso legal](https://ine.es/dyngs/AYU/index.htm?cid=125), con la
cita «Elaboración propia con datos extraídos del sitio web del INE: www.ine.es» y la fecha de
actualización. La metodología no añade condiciones.

## Descarga propuesta

Por la API Tempus (JSON con el código de sección), o por el CSV de cada tabla. Tamaños estimados
(el INE no da el tamaño de antemano):

| Opción | Qué | Tamaño estimado |
| --- | --- | --- |
| A | Renta (31097) y demografía (31105) del último año (2024), cruzadas con la cartografía de 2025 | ~10 MB |
| B | A + los diez años de las dos tablas y las cartografías 2016–2024 para cruzarlos bien | ~70 MB de tablas + ~450 MB de cartografías (9 × ~50 MB) |
| C | A + los diez años de las dos tablas, cruzando con 2025 solo las secciones cuyo polígono no cambió | B, pero las cartografías solo se usan para comparar y no se guardan todas |

La tabla 37727 (Gini) añade ~2 MB por año si se quiere.
