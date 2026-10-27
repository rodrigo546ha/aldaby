# ADR-0001: La IA explica; los motores calculan

**Estado:** Aceptada · **Fecha:** 2026-10-27 · **Decide:** Rodrigo

## Contexto
El usuario toma decisiones de cientos de miles de euros con el plan. Un LLM puede equivocarse o
inventar cifras, y una cifra errónea destruye la confianza, que es el producto.

## Decisión
Ninguna cifra mostrada al usuario la genera el LLM. Los cálculos viven en motores deterministas
(`engines/`) y modelos estadísticos; toda cifra es un `Figure` con fórmula y fuentes. El agente solo
llama a herramientas y redacta sobre cifras ya calculadas.

## Opciones consideradas
- **LLM con razonamiento numérico:** rápido de construir, no auditable, irreproducible. Descartada.
- **Motores + LLM explicativo:** más trabajo inicial, auditable y testeable. Elegida.

## Consecuencias
- Cada regla de negocio necesita un test con valor conocido.
- Evaluación en F6: ninguna cifra del texto del agente puede faltar en los `Figure` del plan.
