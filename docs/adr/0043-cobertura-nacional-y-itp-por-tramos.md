# ADR-0043: Cobertura nacional por oferta y ITP por tramos

**Estado:** Aceptada · **Fecha:** 2026-11-03 · **Decide:** Rodrigo («Sí, por oferta»)

## Contexto
Rodrigo quiere que la herramienta cubra toda España. Hasta ahora todo lo que necesita un plan
estaba cargado solo para Madrid: secciones con renta, referencias de alquiler, índices, Catastro y
normativa autonómica y municipal. Las ventas del Patrimonio en Ourense o un piso de agencia en
Valencia no se podían valorar.

Hay dos partes:
- **Datos públicos.** Son mecánicos: los cargadores ya existían y solo había que dárselos por
  provincia o por comunidad.
- **Normativa.** Cada regla autonómica sale de su ley y la tiene que verificar Rodrigo (regla de
  oro 2).

## Decisión
1. **Datos públicos de toda España** con los cargadores de siempre:
   - IPV y componente de alquiler del IPC por comunidad;
   - estadística del Catastro de todos los municipios;
   - SERPAVI por provincia;
   - cartografías de 2016 a 2024 y Atlas de renta del INE de las 52 provincias.

   Las tablas del Atlas de cada provincia van en `data/territory/adrh_tablas.yaml`, sacadas de la
   API del INE (cómo, en el fichero).
2. **Normativa autonómica por orden de oferta**: primero las comunidades con más compraventas de
   vivienda (INE, ETDP, tabla 6150). La tanda 6 trae Andalucía, Cataluña y Comunitat Valenciana:
   - ITP y AJD;
   - escala autonómica del IRPF y mínimos propios;
   - zona tensionada;
   - alquiler turístico;
   - plusvalía de las ciudades principales.

   Todo va con `verified: false` y la lista de comprobación en `docs/normativa/`. La tanda 7 trae
   Castilla y León, Castilla-La Mancha, Murcia, Galicia y Canarias. Las demás comunidades vienen
   después, por el mismo orden. El País Vasco y Navarra, con su IRPF foral,
   necesitan antes cambios en el motor.
3. **IBI de todos los municipios de más de 1.000 habitantes** de las 17 comunidades de régimen común,
   desde los PDF del Ministerio de Hacienda (`hacienda_ibi`, ADR-0022). El nombre de la carpeta y
   del fichero de cada comunidad sale del libro completo del año.
4. **ITP por tramos.** `impuesto_compra_segunda_mano` admite:
   - `rate`, un tipo único sobre todo el precio;
   - `brackets`, con dos formas de aplicarse:
     - progresiva: cada tipo solo en la parte del precio de su tramo, como Cataluña;
     - con `whole_value: true`: el tipo del tramo en que cae el precio se aplica a todo el precio,
       como la Comunitat Valenciana por encima de 1.000.000 €.

   `purchase_tax_rate` (el tipo como cifra) solo existe para el tipo único.

## Consecuencias
- Los planes de las tres comunidades salen con cifras provisionales hasta que Rodrigo verifique la
  tanda 6. Las de las demás comunidades siguen sin poder calcularse: el error dice qué regla falta.
- La plusvalía de los municipios sin ordenanza cargada no se calcula. El PDF de Hacienda trae
  también el tipo y los coeficientes de la plusvalía de cada municipio: es la siguiente fuente.
