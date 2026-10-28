# Reglas de normativa

Cada archivo `*.yaml` de esta carpeta es una lista de reglas que carga `RuleBook.from_dir`.
Una ley que cambia se refleja añadiendo una regla nueva con su vigencia, nunca editando código.

## Esquema

```yaml
- id: madrid-itp-2026              # único y estable
  kind: impuesto_compra_segunda_mano
  territory: ES-13                 # ES | ES-<ccaa INE> | ES-<ccaa>-<municipio INE>
  effective_from: 2026-01-01
  effective_to: null               # null = sin fin conocido
  status: vigente                  # vigente | pendiente_convalidacion | derogada
  verified: false                  # true solo tras revisión humana de la fuente
  verified_by: null                # obligatorio con verified: true: quién leyó la fuente
  verified_on: null                # obligatorio con verified: true: cuándo (ISO 8601)
  params: {rate: 0.00}             # parámetros que consume el motor
  source_url: https://www.boe.es/...
  notes: "Qué dice la norma, en una frase"
```

## Reglas de oro

- Ninguna regla entra con `verified: true` sin haber leído la fuente oficial (BOE o boletín autonómico).
- Las reglas sin verificar no se aplican salvo con `allow_unverified=True` (solo para desarrollo).
- Las normas pendientes de convalidación se cargan con `status: pendiente_convalidacion`
  y se usan en escenarios, no en el cálculo base.
- Dos reglas del mismo `kind`, territorio y estado no pueden solaparse en el tiempo: al cambiar
  una ley, la regla anterior se cierra con `effective_to` igual al `effective_from` de la nueva.
- `plantilla.yaml.example` es un ejemplo: no se carga y sus valores no son reales.

## Tipos de regla

Cada `kind` tiene un esquema de `params` en `src/housefinder/regulation/kinds.py`. Una regla de
un tipo desconocido o con parámetros que no encajan no se carga. Para un tipo nuevo, primero se
añade su esquema al catálogo.

| `kind` | `params` |
| --- | --- |
| `impuesto_compra_segunda_mano`, `iva_vivienda_nueva`, `amortizacion_inmueble_alquiler`, `tipo_ibi` | `rate` en tanto por uno |
| `reduccion_irpf_alquiler` | `cases`: lista de `{condition, reduction}`, sin condiciones repetidas |
| `escala_irpf_general`, `escala_irpf_ahorro` | `brackets`: lista de `{from, rate}`; el primero desde 0, crecientes |

## Comprobar

```bash
make rules-check
```

Carga la carpeta y lista todos los errores (también lo hace la CI).
