# ADR-0061: Los gastos fijos suben en la TIR con el IPC general de la comunidad

- **Estado:** aceptada
- **Fecha:** 2026-11-05
- **Decide:** Rodrigo («hazlo», sobre cargar el IPC general y hacer crecer los gastos fijos)

## Contexto

Desde ADR-0060 la renta sube en la TIR con el IPC de alquiler, pero la comunidad, el IBI y el
seguro siguen constantes durante todo el horizonte. Con la renta subiendo y esos gastos quietos, la
TIR sale algo optimista.

## Decisión

1. **Fuente nueva:** el índice general del IPC por comunidad. Es la tabla 76136 del INE, de la
   misma familia y base (2025) que la del alquiler, con datos mensuales desde 2002.
   - **Acceso:** la API del INE (`servicios.ine.es`) no publica `robots.txt`; da 404.
   - **Carga:** `make ipc-general` o el trabajo semanal `ine_ipc_general`. Las 19 comunidades
     vienen en la misma tabla y se cargan a la vez.
2. **Subida anual de los gastos fijos:** el mismo método que la renta (ADR-0060). Es la mediana del
   crecimiento anual compuesto de las ventanas mensuales del IPC general de la comunidad de la
   duración del horizonte. Va como la cifra `assumption.cost_growth`.
3. **Qué sube:** la cuota de la comunidad, el IBI y el seguro, desde el segundo año, como
   gasto × (1 + subida)^(año − 1). La gestión, el mantenimiento y el vacío ya suben con la renta.
4. **Dónde:** igual que la renta, la TIR de cada escenario y la serie del cash flow año a año. El
   primer año, la prueba de estrés y el plazo no cambian.

## Consecuencias

- La TIR baja algo respecto a ADR-0060, y queda menos optimista.
- **El IBI no sigue al IPC.** Sigue al valor catastral y al tipo que fija cada ayuntamiento. El IPC
  es una aproximación y queda dicho en la fórmula. Las revisiones catastrales y los cambios de
  tipo no se pueden prever.
- Sin IPC general cargado para la comunidad, los gastos fijos quedan constantes y el plan lo dice.
