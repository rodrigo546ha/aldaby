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
  params: {rate: 0.00}             # parámetros que consume el motor
  source_url: https://www.boe.es/...
  notes: "Qué dice la norma, en una frase"
```

## Reglas de oro

- Ninguna regla entra con `verified: true` sin haber leído la fuente oficial (BOE o boletín autonómico).
- Las reglas sin verificar no se aplican salvo con `allow_unverified=True` (solo para desarrollo).
- Las normas pendientes de convalidación se cargan con `status: pendiente_convalidacion`
  y se usan en escenarios, no en el cálculo base.
- `plantilla.yaml.example` es un ejemplo: no se carga y sus valores no son reales.
