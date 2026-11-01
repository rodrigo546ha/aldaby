# ADR-0022: Supuestos del plan estimados desde fuentes públicas

- **Estado:** aceptada (decisiones de Rodrigo, 2026-10-31)
- **Fecha:** 2026-10-31
- **Tarea:** F6.5 (búsqueda inversa)

## Contexto
Para puntuar ofertas con el plan del usuario (`planning/simulate.py`) hacen falta supuestos que los
anuncios no traen: tipo de la hipoteca, subida de tipos del estrés, IBI, valor de la construcción
(base de la amortización), comunidad, seguros, mantenimiento, vacío, gestión y gastos de compra y
de venta no regulados. Rodrigo pidió estimarlos con datos reales, «acercándonos lo máximo
posible», y no dejarlos al usuario ni a valores de memoria. Investigación de fuentes
(2026-10-31): todas oficiales, con reutilización citando la fuente y sin `robots.txt` que bloquee
las rutas.

## Decisión

### Fuentes (cada una con su cargador y su registro en `sources`)
| Fuente | Qué se carga | Formato | Condiciones |
| --- | --- | --- | --- |
| Banco de España, Boletín Estadístico, tabla 19.4 (`be1904.csv`) | TEDR de nuevas operaciones de crédito a la vivienda por periodo de fijación inicial, mensual, nacional | CSV | Citar al Banco de España, sin manipular los datos |
| INE, Estadística de Hipotecas, tabla 76315 | Tipo medio al inicio de las hipotecas sobre viviendas (fijo, variable y total), mensual, nacional: solo contraste | API Tempus | INE, citando la fuente |
| Catastro, estadísticas anuales urbanas por municipio (`URBANA{año}.xls`) | Inmuebles y valor catastral residenciales, y valor de suelo y construcción (todos los usos) | XLS (con `xlrd`, BSD) | Reproducción autorizada citando el origen |
| Ministerio de Hacienda, Oficina Virtual EELL, «Tipos de gravamen» por comunidad (PDF) | Tipo del IBI urbano de cada municipio | PDF (con `pypdf`) | Reutilización citando la fuente |
| INE, Encuesta de Presupuestos Familiares, tabla 73993 | Gasto medio por hogar y comunidad en gastos comunitarios, seguros de la vivienda y mantenimiento | API Tempus | INE, citando la fuente |

El tipo del IBI es normativa: no va a `market_references` sino a reglas `tipo_ibi`
(`data/rules/ibi_hacienda_{año}.yaml`), generadas desde el PDF con `verified: false` y la URL del
PDF como fuente. Un municipio que ya tiene su regla (la de Madrid, de su ordenanza) no se pisa.
Las cifras que dependen de ellas salen PROVISIONALES hasta que Rodrigo las verifique (ADR-0003).

El PDF de cada comunidad trae los municipios de más de 1.000 habitantes (131 de los 179 de
Madrid); en los demás no hay tipo del IBI y la búsqueda lo avisa.

`market_references` admite el nivel `pais` (código `ES`) para las series nacionales (migración
0013).

### Estimación por oferta (`valuation/assumptions.py`), cada cifra un `Figure` con su fuente
- **Tipo de la hipoteca:** último TEDR de la vivienda a más de diez años de fijación (la hipoteca
  del simulador es a tipo fijo). Es el tipo de mercado, no el del perfil del usuario, y no incluye
  comisiones: la nota lo dice.
- **Subida del estrés:** la mayor subida de ese mismo tipo en veinticuatro meses en la serie desde
  2003. Sale de la historia, no de una opinión.
- **Valor catastral estimado:** valor catastral residencial medio del municipio (valor / número de
  inmuebles residenciales). No se puede ajustar por superficie: el Catastro no publica la
  superficie construida residencial por municipio.
- **IBI:** valor catastral estimado × tipo del IBI del municipio.
- **Valor de la construcción:** precio × (valor de construcción / valor catastral) del municipio,
  con todos los usos (no hay reparto solo residencial).
- **Comunidad:** la del anuncio si la dice (campo confirmado por el usuario); si no, el gasto medio
  por hogar en gastos comunitarios de la comunidad autónoma (EPF). Es una media de todos los hogares,
  también los que no pagan comunidad: **se queda corta** y la nota lo dice.
- **Seguros:** gasto medio por hogar en seguros ligados a la vivienda (EPF). Solo hogar, no impago.
- **Mantenimiento:** gasto medio por hogar en mantenimiento y reparaciones (EPF), como proporción de
  la renta estimada de la oferta.

### Lo que no tiene fuente oficial
Vacío, gestión (si el usuario la delega), gastos de compra no regulados (gestoría, tasación) y
gastos de venta los pone el usuario en su perfil («supuestos de búsqueda»). No tienen valor por
defecto en el código (regla 4): mientras falten, la búsqueda lo dice y no puntúa.

## Opciones consideradas
- **Parámetros PROVISIONAL con valores por defecto:** cómodo, pero serían cifras sin fuente.
- **Que el usuario ponga todos los supuestos:** descartado por Rodrigo: hay fuentes para la mayoría.
- **Tipos por perfil (edad, LTV, ingresos):** ninguna fuente pública los publica así.

## Consecuencias
- Cinco cargadores nuevos (`make supuestos` los ejecuta todos) y la dependencia `xlrd`.
- Las estimaciones son medias de zona o nacionales: cada una dice su límite en la nota del `Figure`,
  y el usuario puede corregirlas en el plan.
- Los datos se actualizan con la fuente: BdE e INE cada mes, Catastro, Hacienda y EPF cada año.
