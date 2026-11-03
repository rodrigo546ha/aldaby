# ADR-0044: Plusvalía municipal de todos los municipios desde el libro de Hacienda

**Estado:** Aceptada · **Fecha:** 2026-11-03 · **Decide:** Rodrigo («Sí, sácala»)

## Contexto
Hasta ahora la plusvalía municipal (IIVTNU) solo se podía calcular en las 25 ciudades con ordenanza
leída (tandas 6 a 8). En cualquier otro municipio, el plan fallaba al llegar a la venta si había
valores catastrales.

El PDF anual «Tipos de gravamen, índices y coeficientes» del Ministerio de Hacienda, el mismo del
que sale el IBI (ADR-0022), tiene en su tercera parte dos tablas para los municipios de más de
1.000 habitantes que tienen establecido el impuesto, cada una con 21 periodos de generación:
- los coeficientes sobre la base imponible;
- el tipo de gravamen.

El servidor no tiene robots.txt (devuelve 404) y la reutilización está permitida citando la fuente.

Antes de decidir se compararon las 25 ordenanzas leídas con el libro de 2026. Todas coinciden,
incluidos los tipos por años de tenencia de Gijón y Toledo. Huesca, cuya ordenanza aparece como
derogada, no está en la lista de municipios con el impuesto.

## Decisión
1. **`python -m housefinder.ingestion.hacienda_plusvalia --year AAAA`** escribe
   `data/rules/plusvalia_hacienda.yaml` (generado, sin verificar). Tres tipos de regla:
   - **Tipo:** `tipo_plusvalia` de cada municipio con el impuesto. Si es igual en los 21 periodos
     es un tipo único; si no, va por años de tenencia (`by_years`, ADR-0043).
   - **Coeficientes:** `coeficientes_plusvalia` solo si no son los máximos legales vigentes (la
     regla de `ES`). El municipio que aplica los máximos sigue a esa regla cuando la ley los
     cambie. Donde un coeficiente propio pase del máximo, se aplica el máximo (TRLRHL,
     art. 107.4), como ya hacía el motor.
   - **Sin impuesto:** tipo 0 para los municipios que están en la tabla del IBI pero no en la de
     la plusvalía. La tabla del IBI tiene todos los de más de 1.000 habitantes, y el título de la
     tabla de la plusvalía dice «que tienen establecido el impuesto».
2. **Vigencia:** las reglas rigen desde el 1 de enero del año del libro y no tienen fecha de fin,
   porque la plusvalía se calcula a la fecha de venta del plan, años después. El fichero se rehace
   entero con cada libro nuevo, así que no tiene año en el nombre.
3. **Las ordenanzas leídas mandan.** Un municipio que ya tiene su regla en otro fichero no se toca.
   Si su tipo no coincide con el del libro, el generador lo avisa para revisarlo.
4. **Fuera de este fichero** (Ceuta y Melilla sí están: su bonificación va en reglas propias,
   ADR-0045):
   - el País Vasco y Navarra, que no están en el libro (régimen foral);
   - los municipios de 1.000 habitantes o menos, que tampoco están en el libro.
5. **La columna «Porc. reducc.»** de la tabla de coeficientes no se modela. Cuando no es cero, se
   menciona en la nota de la regla.

## Consecuencias
- 2.271 municipios de régimen común tienen tipo de plusvalía (305 de ellos por años de tenencia);
  578 tienen tipo 0 y 1.127 tienen coeficientes propios.
- Guadalajara entra con el tipo del libro (30 % hasta 18 años, 25 % a los 19, 18 % desde 20). Su
  web bloquea a los agentes de Anthropic, así que su ordenanza no se ha leído directamente.
- Las cifras son del libro, no de cada ordenanza: un cambio aprobado después de que Hacienda
  publique el libro no se ve hasta el del año siguiente.
- Las reglas son unas 4.000 en un fichero de unos 2 MB. Para que cargar las reglas no se haga
  lento, `core/dated.py` las lee con el lector seguro en C de PyYAML (libyaml), cuando está: lee lo
  mismo que `yaml.safe_load`. La carga de todas las reglas tarda 0,35 s, frente a 2 s con el
  lector en Python.
