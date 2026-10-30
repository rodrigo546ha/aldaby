# F5.1 y F5.2 · Fuentes públicas de referencia de alquiler y de precio

**Fecha:** 2026-10-30 · Comprobado en las páginas oficiales salvo donde se indica. Sin descargas de
datos todavía.

## Conclusión
- **Alquiler, por sección censal: sí.** El SERPAVI del Ministerio de Vivienda da, por sección
  censal, la mediana, el P25 y el P75 de la renta en €/m² al mes, de 2011 a 2024, con reutilización
  libre (también comercial) citando la fuente y la fecha. Es la base natural del modelo de renta
  (F5.3).
- **Precio de venta, por sección censal: no hay fuente pública reutilizable.** Lo más fino que se
  puede reutilizar es el valor tasado por municipio (más de 25.000 habitantes). El Notariado tiene
  código postal, pero prohíbe el uso comercial. El modelo de precio (F5.4) tal como lo plantea el
  plan, por sección, no se puede hacer solo con datos abiertos oficiales. Opciones al final.

## Alquiler

### SERPAVI (Ministerio de Vivienda y Agenda Urbana) — candidata principal
- **Qué es.** Explotación del IRPF (alquileres de vivienda habitual declarados) con la superficie del
  Catastro. Por unidad territorial: número de viviendas y mediana, P25 y P75 de renta (€/m² mes),
  cuantía (€/mes) y superficie (m²), separando vivienda colectiva y unifamiliar.
- **Granularidad.** «sección censal, distrito, municipio, provincia y comunidad autónoma», con el
  seccionado del Censo 2021 (que ya tenemos cargado).
- **Cobertura.** En 2024, 26.137 de 36.293 secciones de España (72,0 %) tienen datos de vivienda
  colectiva: solo se publica con «un número de testigos mínimo de 10». En la Comunidad de Madrid,
  474.935 viviendas alquiladas declaradas en 2024.
- **Años.** «disponible para los años 2011 a 2024». La página de descargas ofrece «la base de
  datos … para los años 2011-2024 (Excel)»: `BD Sistema Estatal Índices de Alquiler de Vivienda`,
  67,8 MB, en `cdn.mivau.gob.es`.
- **Reutilización.** Aviso legal del Ministerio: «autorizada su reproducción total o parcial,
  modificación, distribución y comunicación, para usos comerciales y no comerciales», sin
  desnaturalizar el contenido, citando la fuente y «la fecha de la última actualización».
- **Límites.** Solo alquileres declarados en el IRPF por personas físicas (no ofertas ni contratos
  nuevos); secciones con menos de 10 alquileres, vacías; año t disponible con un año y medio de
  retraso.
- Fuentes: <https://www.mivau.gob.es/vivienda/alquila-bien-es-tu-derecho/serpavi>, metodología de
  18/03/2026 (`cdn.mivau.gob.es/.../2026-03-18_Metodologia_SERPAVI.pdf`), aviso legal
  <https://www.mivau.gob.es/ministerio/aviso-legal>.

### Otras de alquiler
- **INE, Índice de Precios de Vivienda en Alquiler (IPVA).** Índice de variación (base 2015), no
  niveles de renta; hasta municipio y distrito de capitales. Útil para actualizar el último año del
  SERPAVI, no como base. (Informe del agente, sin comprobar aquí.)
- **Fianzas de la Comunidad de Madrid.** Recuentos de trámites, sin rentas. No sirve.
- **Copias del Ayuntamiento de Madrid.** Solo la capital; sus páginas no se han podido comprobar
  (las direcciones que dio la búsqueda no existen). No hacen falta teniendo el original.

## Precio de venta

| Fuente | Qué mide | Granularidad | Reutilización | ¿Sirve? |
| --- | --- | --- | --- | --- |
| Portal Estadístico del Notariado | €/m² de compraventas escrituradas | Código postal | «no permitiéndose el uso comercial» | No, sin autorización escrita |
| Ministerio de Vivienda, valor tasado | €/m² de tasación, vivienda libre, trimestral | Municipio de más de 25.000 hab. | Aviso legal del Ministerio: libre citando fuente y fecha | Sí, a nivel municipal |
| Ministerio de Vivienda, transacciones | Número de compraventas | Municipio | Ídem | Como peso o liquidez, no precio |
| Registradores (Estadística Registral) | Índice de ventas repetidas, €/m² | Sin comprobar | Sin comprobar (PDF) | Pendiente |
| INE, Índice de Precios de Vivienda | Índice de precios escriturados | Comunidad autónoma | Reutilizable citando al INE | Para la revalorización (F5.5) |
| Catastro, valor de referencia | Base imponible mínima por inmueble | Inmueble, consulta una a una | Licencia al descargar; sin descarga masiva | No para el modelo; sí como dato del inmueble |

Comprobado aquí: Notariado (términos de uso, por el agente con cita), valor tasado (metodología del
Ministerio). El resto, informe del agente.

## Opciones para el precio (F5.4)
1. **Valor tasado municipal con rango ancho.** Honesto pero grueso: todo Madrid capital con el mismo
   €/m².
2. **Precio desde la renta.** Precio por sección = renta del SERPAVI de la sección × relación
   precio/renta del municipio (valor tasado municipal / renta mediana municipal del SERPAVI). Da
   variación por sección con fuentes oficiales, pero supone que la rentabilidad es igual en todo el
   municipio: es un supuesto, no un dato, y tiene que ir marcado como tal en la `Figure`.
3. **Pedir autorización al Notariado** para su dato por código postal (tarea humana, como la
   consulta a la AEBOE).
4. **El precio pedido de la oferta** como referencia del propio inmueble, contrastado con 1 o 2.
   La negociación sobre el precio pedido (F5.4) no tiene fuente pública.

## Descargas que harían falta
- SERPAVI 2011–2024 (Excel, 67,8 MB, Ministerio de Vivienda).
- Valor tasado por municipio (tablas del boletín estadístico del Ministerio, pequeñas).
- INE IPV por comunidad autónoma (API del INE, pequeña), para F5.5.
