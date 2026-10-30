# F5.6 · Backtesting del modelo de renta y precio

**Fecha:** 2026-10-30 · **Datos:** SERPAVI 2011–2024 (provincia de Madrid, vivienda colectiva),
valor tasado municipal 2005–2025 y IPV de la Comunidad de Madrid, ya cargados.
**Reproducir:** `python -m housefinder.valuation.backtest --province 28 --region 13`.

## Qué se mide y qué no
- **Renta por sección:** con los datos del año t, la mediana de €/m² estimada para la sección
  (contraída hacia el municipio con cada k) frente a la mediana real de t + h. Dos versiones: tal
  cual funciona el modelo, sin actualizar, y descontando la variación del municipio entre t y
  t + h, que aísla el error de la zona.
- **Actualización con el IPV:** valor tasado municipal de t+1 = el de t × IPV medio de t+1 / de t.
- **Relación precio/renta de un año antes:** valor tasado de t+1 = renta municipal de t+1 × 12 ×
  la relación de t.
- **No se mide el precio por sección:** no hay precio público por sección con el que compararlo.
- **No se mide la renta de un inmueble concreto:** el SERPAVI no publica rentas individuales. Lo
  que se mide es la mediana de la sección; el rango P25–P75 que muestra el modelo es la dispersión
  de los alquileres de la sección, y es mucho más ancho que estos errores.

Métricas: mediana del error relativo (MdAPE), error absoluto medio en €/m² mes (MAE) y parte de
las estimaciones a menos de un 10 % del valor real.

## Renta: contracción hacia el municipio (k)
53.237 estimaciones (sección y año) a un año, descontada la variación municipal:

| k | MdAPE | MAE €/m² | ±10 % |
| --- | --- | --- | --- |
| 0 (solo la sección) | **2,08 %** | 0,27 | 97,3 % |
| 2 | 2,14 % | 0,27 | 97,0 % |
| 10 (supuesto inicial) | 2,52 % | 0,34 | 93,7 % |
| 40 | 4,13 % | 0,58 | 81,7 % |
| 160 | 7,41 % | 0,98 | 62,1 % |
| Solo el municipio | 11,04 % | 1,44 | 46,6 % |

A dos y tres años, descontada la variación municipal, el orden es el mismo (k = 0: 2,59 % y
3,01 %; k = 10: 2,97 % y 3,33 %). Por tamaño de sección, con k = 0 frente a k = 10: de 10 a 29
alquileres, 3,38 % frente a 5,78 %; de 30 a 99, 2,22 % frente a 2,79 %; 100 o más, 1,60 % frente a
1,69 %.

**Decisión:** k = 0, sin contracción. Cada sección se aparta de su municipio de forma estable, y
contraer borra esa diferencia. Registro `contraccion-renta-backtesting-2026-10` en
`data/params/valoracion.yaml`, ya no provisional.

**Cautela:** los mismos contratos se declaran varios años seguidos, así que la mediana de t+1 no es
independiente de la de t. Eso favorece a k = 0, pero no explica una diferencia tan grande ni que se
mantenga a tres años.

## Renta: cuánto se queda corta una renta antigua
Sin descontar nada, con k = 0, mediana de (estimado − real) / real:

| Antigüedad de la renta | Toda la serie | Desde 2021 (2021→2023 y 2022→2024) |
| --- | --- | --- |
| 1 año | −2,30 % | — |
| 2 años | −5,12 % | **−7,95 %** |

El modelo usa la renta de 2024 a finales de 2026: dos años. Con el ritmo reciente, **se queda
corto en torno a un 8 %**, y el aviso actual («no se actualiza con ningún índice») no lo cuantifica.

## Precio
| Prueba | Casos | MdAPE | MAE €/m² | ±10 % |
| --- | --- | --- | --- | --- |
| Actualización del valor tasado con el IPV, a un año | 485 | 2,99 % | 78 | 93,2 % |
| Relación precio/renta del año anterior | 349 | 2,64 % | 70 | 94,0 % |

Los dos pasos del precio que se pueden medir funcionan a nivel municipal. El supuesto principal, la
misma rentabilidad en todo el municipio, no se puede medir con datos públicos.

## Pendiente
- **El umbral de error aceptable lo fija F0** (criterio de salida de F5). Estas cifras son la
  referencia para fijarlo.
- ~~Actualizar la renta~~: hecho con el componente de alquiler del IPC (ver abajo).

## Renta actualizada con el IPC de alquiler (2026-10-30)
Mediana de la sección de t × IPC de alquiler medio de t + h / de t, frente a la real de t + h:

| Antigüedad | Sesgo sin actualizar | Sesgo con IPC | Error mediano sin / con IPC |
| --- | --- | --- | --- |
| 1 año (desde 2022) | −4,21 % | −1,89 % | 4,23 % / 2,12 % |
| 2 años (toda la serie) | −5,12 % | −3,44 % | 6,92 % / 4,80 % |
| 2 años (desde 2021) | −7,95 % | −4,18 % | 7,95 % / 4,23 % |

El IPC mide todos los contratos en vigor, también los antiguos, y sube más despacio que la mediana
del SERPAVI: corrige la mitad del desfase. El resto se dice en el aviso de la cifra.
