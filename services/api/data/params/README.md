# Parámetros con fecha

Cada archivo `*.yaml` de esta carpeta es una lista de parámetros que carga `ParamBook.from_dir`
(ADR-0005). Son datos que no son normativa: criterios bancarios, trayectoria del Euríbor…
Un cambio se refleja añadiendo un registro nuevo con su vigencia, nunca editando código.

## Esquema

```yaml
- id: criterios-banco-x-2027       # único y estable en toda la carpeta
  kind: criterios_bancarios
  territory: ES                    # ES | ES-<ccaa INE> | ES-<ccaa>-<municipio INE>
  effective_from: 2027-01-01
  effective_to: null               # null = sin fin conocido
  provisional: false               # true mientras no haya fuente documentada
  params: {max_ltv: 0.70, max_dti: 0.35, max_age_at_end: 75, max_years: 30}
  source: "Qué banco o intermediario y cuándo, en una frase"
  source_url: https://...          # opcional
  notes: ""
```

## Reglas

- Un parámetro sin fuente documentada va con `provisional: true`. Se usa, pero toda cifra que
  dependa de él sale marcada como provisional.
- Gana el registro vigente más específico por territorio y, a igualdad, el más reciente.
- Un `id` repetido es un error de carga.

## Tipos

| `kind` | `params` |
| --- | --- |
| `criterios_bancarios` | `max_ltv` y `max_dti` en tanto por uno (0, 1]; `max_age_at_end` y `max_years` enteros positivos |
| `trayectoria_euribor_3m` | Ronda de proyecciones del BCE (ADR-0006): `round`, `cut_off`, `series`, `unit: percent` y `quarters` (`2026-Q3: 2.5`, consecutivos), copiados tal cual de la API |
| `euribor_12m_oficial` | Euríbor a un año del BOE: `month` (`2026-07`), `unit: percent` y `value`, copiados tal cual de la resolución mensual |
