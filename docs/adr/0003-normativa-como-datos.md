# ADR-0003: La normativa son datos versionados

**Estado:** Aceptada · **Fecha:** 2026-10-27 · **Decide:** Rodrigo

## Contexto
La normativa de vivienda cambia con frecuencia (decretos, convalidaciones, cambios autonómicos) y
afecta directamente a la rentabilidad. Codificarla en el programa obliga a desplegar con cada cambio.

## Decisión
Cada regla es un registro en `data/rules/*.yaml` con territorio, vigencia, estado
(`vigente`, `pendiente_convalidacion`, `derogada`), fuente oficial y verificación humana. El motor
`RuleBook` resuelve la regla más específica vigente en una fecha y permite escenarios con reglas pendientes.

## Consecuencias
- Cambiar una ley = añadir una regla y verificarla.
- Los planes registran qué reglas aplicaron (`plans.rule_ids`) y son reproducibles.
- Se necesita un proceso de vigilancia del BOE y boletines (F2.6).
