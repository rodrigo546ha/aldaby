# F5.5 · ¿Explican los factores locales la revalorización?

**Fecha:** 2026-10-30 · **Datos ya cargados:** SERPAVI 2011–2024 (renta mediana de vivienda
colectiva por sección, municipio y provincia), Atlas de renta del INE 2015–2024 (renta neta media
por persona y población por sección), valor tasado municipal 2005–2025 e IPV de la Comunidad de
Madrid 2007–2026. Sin descargas nuevas. Scripts de exploración, no código del proyecto.

## 1. La historia del precio
Revalorización anual compuesta en ventanas de 10 años:

| Serie | Ventanas | P25 | Mediana | P75 | Mín.–máx. |
| --- | --- | --- | --- | --- | --- |
| Valor tasado, Madrid capital (2005–2025) | 11 | −2,8 % | 0,0 % | +3,9 % | −3,5 % a +7,3 % |
| Valor tasado, Getafe | 11 | −6,1 % | −2,0 % | +2,7 % | −6,9 % a +7,4 % |
| IPV, Comunidad de Madrid (2007–2026) | 38 | +0,5 % | +2,4 % | +6,1 % | −3,0 % a +7,5 % |

Dos ciclos escasos, dominados por la caída de 2008–2013 y la subida desde 2015.

## 2. Factores frente a la renta (la renta es la serie larga con detalle por zona)
Crecimiento del logaritmo de la renta mediana a 3 años, **relativo** a la zona que contiene la
unidad. Ajuste con t = 2018 y 2019; prueba fuera de muestra con t = 2020 y 2021 (es decir,
2023 y 2024). Mínimos cuadrados.

**Secciones frente a su municipio** (3.963 secciones con el mismo polígono en las cartografías
2016–2025; 7.465 casos de ajuste, 7.496 de prueba):

| Modelo | Error medio | Error mediano |
| --- | --- | --- |
| Crece como su municipio (cero) | 3,15 % | 2,46 % |
| Crecimiento de la renta del hogar y de la población (3 años previos) | 3,16 % | 2,46 % |
| Más nivel de renta del hogar y de alquiler relativos | 3,17 % | 2,49 % |

Ningún factor mejora a «crece como su municipio».

**Municipios frente a la provincia** (252 casos de ajuste, 259 de prueba):

| Modelo | Error medio | Error mediano |
| --- | --- | --- |
| Crece como la provincia (cero) | 3,85 % | 2,16 % |
| Nivel de alquiler relativo (convergencia) | **3,46 %** | **1,98 %** |
| Crecimiento de la renta del hogar y de la población | 3,80 % | 2,53 % |
| Todo | 3,47 % | 2,14 % |

Solo el nivel de alquiler aporta algo: los municipios más baratos que la provincia suben algo más
(coeficiente −0,063: un 10 % por debajo, unos 0,6 puntos más en 3 años). La renta del hogar y la
población no aportan.

## 3. Lo que domina es el mercado entero
A 3 años, la renta de la provincia subió un 10,3 % (2020→2023) y un 12,8 % (2021→2024); la
mediana del crecimiento municipal fue un 13 %. Las diferencias entre zonas son de ±3–4 %. Los
factores locales explican, como mucho, una parte pequeña de esas diferencias, y nada del ciclo.

## 4. La convergencia cambia de signo con el ciclo
Coeficiente b (crecimiento relativo a 3 años = b × brecha logarítmica de renta frente a la
provincia, sin constante), por año de partida: 2011 +0,065; 2012 +0,065; 2013 +0,044;
2014 +0,020; 2015 +0,015; 2016 +0,045; 2017 +0,019; 2018 −0,026; 2019 −0,077; 2020 −0,059;
2021 −0,037. Toda la serie: −0,0002. Tras la crisis los municipios caros se alejaron; en la subida
desde 2018 los baratos se acercaron. La validación de la sección 2 (ajuste 2018–2019) cayó en la
fase de convergencia.

## Decisión (Rodrigo, 2026-10-31)
Escenarios = ciclo de la comunidad (P25, mediana y P75 de las ventanas del IPV de la duración del
horizonte) + convergencia como dimensión del escenario: base con el b global; optimista con el b
(P25 o P75 de los periodos) que favorece al municipio; conservador, con el otro. Parámetro
`convergencia_municipal` en `data/params/valoracion.yaml`. Empleo y oferta nueva no se cargan: el
empleo por municipio solo está en datos.comunidad.madrid (robots.txt prohíbe el acceso automático)
y la oferta nueva no se publica por municipio.

Con los datos reales, a 10 años: Madrid −0,09 % / 2,03 % / 5,99 %; Getafe −0,21 % / 2,04 % /
5,94 %; Móstoles −0,37 % / 2,04 % / 6,05 %. El ciclo pesa casi todo; el municipio mueve unas
décimas los extremos.
