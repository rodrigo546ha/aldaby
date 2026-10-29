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

## Datos personales

El perfil del usuario y el contenido de sus planes (entradas, cifras y texto) se guardan con cifrado
de sobre AES-256-GCM (ADR-0011): una clave de datos por registro, envuelta con una clave maestra
(fichero local en desarrollo, AWS KMS en producción) y atada a su fila y su organización. En claro
solo van los metadatos para filtrar y auditar. El modelo de perfil se redacta al mostrarse y un test
comprueba que un flujo completo no deja ingresos ni deudas en los logs.

## Stack

Next.js (web) · Python 3.11+ y FastAPI (motores y API) · PostgreSQL 16 + PostGIS · modelo de pesos
abiertos en un servidor propio, detrás de una interfaz propia (ADR-0014) · AWS para el despliegue (F7).
