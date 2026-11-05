# F5.5 · Convergencia municipal en cada comunidad

**Fecha:** 2026-11-05 · **Datos ya cargados:** SERPAVI 2011–2024 de todas las provincias (renta
mediana de vivienda colectiva por municipio y provincia). Sin descargas nuevas. Reproducible con
`make backtest CONVERGENCIA=1` (`valuation/backtest.py`, `regions_convergence`).

## Qué se estima
Lo mismo que para Madrid en `f5-5-factores-revalorizacion.md` (§ 4), en cada comunidad:
- **Brecha:** logaritmo de la renta del municipio frente a la de **su** provincia en el año t.
- **Crecimiento relativo:** crecimiento logarítmico del municipio menos el de su provincia entre t
  y t + 3.
- **Coeficiente b:** de crecimiento relativo = b × brecha, por mínimos cuadrados sin constante. Se
  calcula por año de partida (2011–2021, once periodos) y con todos los años juntos (b global).

Con b < 0, los municipios baratos suben más que su provincia, es decir, convergen.

## Comprobación
Con el código nuevo, Madrid da lo mismo que el parámetro en vigor:

| | b global | P25 | P75 |
| --- | --- | --- | --- |
| Parámetro en vigor | −0,0002 | −0,0313 | +0,0442 |
| Código nuevo | −0,0002 | −0,0312 | +0,0442 |

La diferencia en el P25 es de redondeo.

## Resultados

| Comunidad | Municipios | Casos | b global | P25 | P75 | Base: cero → b global de 2011–2017 |
| --- | --- | --- | --- | --- | --- | --- |
| Andalucía (01) | 332 | 2.711 | −0,0049 | −0,0288 | +0,0134 | 5,44 % → 5,53 % |
| Aragón (02) | 108 | 918 | −0,0416 | −0,0674 | −0,0118 | 5,09 % → 5,75 % |
| Asturias (03) | 50 | 500 | −0,0755 | −0,1426 | +0,0010 | 4,04 % → 5,59 % |
| Illes Balears (04) | 58 | 585 | −0,0103 | −0,0408 | +0,0420 | 4,11 % → 4,31 % |
| Canarias (05) | 79 | 782 | −0,0187 | −0,0445 | +0,0248 | 4,17 % → 4,23 % |
| Cantabria (06) | 60 | 534 | −0,0856 | −0,1426 | −0,0292 | 4,31 % → 4,64 % |
| Castilla y León (07) | 215 | 1.845 | −0,0246 | −0,0261 | −0,0009 | 5,31 % → 5,53 % |
| Castilla-La Mancha (08) | 195 | 1.511 | −0,0519 | −0,1000 | −0,0124 | 6,79 % → 7,30 % |
| Cataluña (09) | 510 | 4.723 | −0,0313 | −0,0400 | −0,0030 | 4,22 % → 4,15 % |
| Comunitat Valenciana (10) | 311 | 2.726 | +0,0085 | −0,0018 | +0,0296 | 5,12 % → 5,18 % |
| Extremadura (11) | 66 | 517 | −0,0332 | −0,0468 | −0,0200 | 6,00 % → 6,26 % |
| Galicia (12) | 172 | 1.668 | −0,0372 | −0,0654 | −0,0010 | 4,47 % → 5,18 % |
| Madrid (13) | 138 | 1.371 | −0,0002 | −0,0312 | +0,0442 | 3,88 % → 4,99 % |
| Región de Murcia (14) | 40 | 412 | −0,0065 | −0,0509 | +0,0526 | 3,61 % → 4,17 % |
| La Rioja (17) | 35 | 275 | −0,0319 | −0,0958 | +0,0100 | 4,73 % → 5,16 % |

La última columna es el error medio del crecimiento relativo a 3 años fuera de muestra. Se ajusta b
con los años de partida 2011–2017 y se prueba con 2018–2021 (de 2021 a 2024). Se compara «crece
como su provincia» (b = 0) con usar el b global de los años anteriores.

**Sin estimación:**
- **País Vasco y Navarra:** el SERPAVI solo los trae desde 2021–2024, porque sus haciendas forales
  no están en los datos de la AEAT. Navarra tiene un solo periodo.
- **Ceuta y Melilla:** un solo municipio cada una, igual a su provincia, así que la brecha siempre
  es cero.

## Lo que dicen los datos
1. **La convergencia existe y cambia con el ciclo.** En la mayoría de comunidades los municipios
   baratos se acercaron a su provincia en 2011–2014, con b entre −0,08 y −0,23. Después el signo va
   y viene. Madrid es la excepción: allí se alejaron hasta 2017.
2. **El b de los años anteriores no predice el siguiente.** Fuera de muestra, usar el b global
   de 2011–2017 empeora el error frente a «crece como su provincia» en 15 de 16 comunidades.
   Cataluña es la única que mejora, y poco: de 4,22 % a 4,15 %.
3. **La prueba de F5.5 da resultados mixtos.** Ajustando con 2018–2019 y probando con 2020–2021,
   b mejora a cero en Madrid, Baleares, Cantabria, Cataluña, Comunitat Valenciana y Murcia. Empeora
   en Aragón, Asturias, Canarias, Castilla y León, Castilla-La Mancha y Extremadura. En Andalucía,
   Galicia y La Rioja queda casi igual.

## Decisión aplicada
Se mantiene el diseño que decidió Rodrigo para Madrid (2026-10-31): la convergencia es una
dimensión del escenario, no una predicción. Con un cambio que piden los datos:
- **Base, b = 0:** el municipio crece como el ciclo de su comunidad. El b global no predice mejor
  que cero (punto 2). En Madrid el b global ya es −0,0002, así que su parámetro no cambia.
- **Extremos, el P25 y el P75 de los b por año, ampliados hasta 0:**
  - en varias comunidades (Aragón, Cantabria, Castilla y León, Castilla-La Mancha, Cataluña,
    Extremadura, Galicia) los dos percentiles son negativos;
  - sin ampliarlos, el escenario conservador de un municipio barato crecería más que el base.
- Parámetros en `data/params/valoracion.yaml`, uno por comunidad, generados desde la salida del
  backtest.

Escenarios a 10 años con los datos reales (conservador / base / optimista):

| Municipio | Conservador | Base | Optimista |
| --- | --- | --- | --- |
| Madrid | −0,09 % | 2,03 % | 5,99 % |
| Getafe | −0,21 % | 2,04 % | 5,94 % |
| Barcelona | −1,17 % | 1,46 % | 5,36 % |
| L'Hospitalet de Llobregat | −1,11 % | 1,46 % | 5,36 % |
| Valencia | −2,12 % | 0,10 % | 3,76 % |
| Sevilla | −1,68 % | 0,51 % | 4,22 % |
| Málaga | −1,65 % | 0,51 % | 4,20 % |
| Zaragoza | −3,24 % | −0,65 % | 3,39 % |
| Bilbao (sin convergencia) | −2,38 % | −0,67 % | 3,08 % |

Como en Madrid, el ciclo de la comunidad pesa casi todo. El municipio mueve unas décimas los
extremos.
