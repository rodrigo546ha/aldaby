# Arquitectura

## Principio

La IA explica; los motores calculan. Tres tipos de componente con responsabilidades separadas:

| Componente | Hace | No hace |
| --- | --- | --- |
| Agente (LLM) | Perfila, extrae datos de anuncios y documentos, orquesta, redacta | Calcular cifras |
| Motores deterministas | Hipoteca, fiscalidad, cash flow, normativa | Llamar a un LLM |
| Modelos estadísticos | Renta, precio, revalorización, vacío, con rango | Dar una cifra sin intervalo |

## Capas

```
Ingesta ──▶ Enriquecimiento ──▶ Motores ──▶ Plan
(BOE,        (geocodificación,    (hipoteca,    (agente que orquesta
 servicers,   duplicados, sección   fiscalidad,   y explica; web y PDF)
 enlaces)     censal, INE, Catastro) normativa,
                                     valoración)
──────────── Base común: PostgreSQL + PostGIS · cola de trabajos · registro de fuentes ────────────
```

## Flujo de un plan

1. El usuario completa su perfil (conversación o formulario) → `user_profiles`.
2. El agente pide a los motores la capacidad de compra → `Figure` con fuentes.
3. La búsqueda inversa puntúa ofertas (`offers`) según el resultado esperado para ese perfil.
4. Para cada oferta elegida, los motores calculan cash flow, estrés y escenarios normativos.
5. El agente redacta el plan sobre esas cifras → `plans` (cifras, reglas aplicadas, texto).

## Trazabilidad

Cada cifra del plan es un `Figure` (ADR-0004): clave estable, valor, unidad, fórmula, fuentes
tipadas (`SourceRef`), fecha y, si es una estimación, rango. Una cifra derivada cita las fuentes de
todas sus entradas, y es `provisional` si alguna lo es. Cada regla legal aplicada queda en
`plans.rule_ids`. Así cualquier plan se puede auditar y reproducir.

## Stack

Next.js (web) · Python 3.11+ y FastAPI (motores y API) · PostgreSQL 16 + PostGIS · Claude en AWS
Bedrock detrás de una interfaz propia · AWS para el despliegue (F7).
