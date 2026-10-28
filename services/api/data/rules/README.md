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
- Un **real decreto-ley** se carga como `pendiente_convalidacion` hasta que el Congreso (o la
  Diputación Permanente) lo convalide, aunque ya esté en vigor: el plan base sigue con la norma
  anterior y el real decreto-ley entra en escenarios. Al convalidarse, pasa a `vigente` y la norma
  anterior se cierra con `effective_to`; si se deroga, pasa a `derogada`. Decidido el 2026-10-28.
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
| `reduccion_irpf_alquiler` | `cases`: lista de `{condition, reduction, when}`, sin condiciones repetidas; `when` son los hechos del contrato que exige el caso (ver abajo) |
| `escala_irpf_general_estatal`, `escala_irpf_general_autonomica`, `escala_irpf_ahorro_estatal`, `escala_irpf_ahorro_autonomica` | `brackets`: lista de `{from, rate}`; el primero desde 0, crecientes. La estatal va en `ES`; la autonómica, en `ES-<ccaa>` |
| `minimo_contribuyente` | `general`, `over_65_extra`, `over_75_extra` en euros |
| `minimo_descendientes` | `first`, `second`, `third`, `fourth_and_more`, `under_3_extra` en euros |
| `limite_intereses_reparacion` | `carryforward_years`: años a los que se arrastra el exceso |
| `zona_tensionada` | `declared` (sí o no) y `checked_through` (fecha de la última resolución trimestral revisada) |
| `regimen_alquiler_habitual`, `regimen_alquiler_temporada`, `regimen_alquiler_habitaciones`, `regimen_alquiler_turistico` | `regime` (texto), `allowed` y `requirements`: lista de `{code, description, source_url}`. Los requisitos de cada nivel territorial se suman |

## Hechos del contrato (`when`)

Cada caso de `reduccion_irpf_alquiler` declara en `when` los hechos que exige, con el vocabulario
de `RentalFacts` (`src/housefinder/regulation/kinds.py`): `contract` (`primer-alquiler`,
`nuevo-contrato`, `prorroga-tacita`), `rent_change` (`rebaja-mas-5`, `no-superior`,
`subida-hasta-5` … `subida-mas-de-20`), `large_holder`, `below_reference_index`, `stressed_zone`,
`young_tenant`, `public_or_social_tenant`, `recent_rehabilitation` y `same_tenant_after_term`.
Un caso sin `when` se aplica siempre. Se aplica el caso de mayor reducción entre los que se
cumplen; si no se cumple ninguno, no hay reducción.

## Comprobar

```bash
make rules-check
```

Carga la carpeta y lista todos los errores (también lo hace la CI).
