# F6.0 · Banco del agente: qwen3 8B frente a 14B (2026-10-31)

Primera comparación de modelos para el agente con herramientas (ADR-0019), en el Mac de desarrollo
(M5, 16 GB) con Ollama. Mismo código, mismas cinco preguntas y misma ventana de contexto
(16.384 tokens); solo cambia `LLM_MODEL_ID`.

```bash
python -m housefinder.advisor evaluar --salida banco.md
LLM_MODEL_ID=qwen3-14b-hf python -m housefinder.advisor evaluar --salida banco-14b.md
```

`qwen3-14b-hf` es `qwen3:14b` (9,3 GB, Apache 2.0) con `num_ctx 16384`, igual que
`infra/ollama/qwen3-hf.Modelfile` para el 8B.

## Preguntas

Sobre la oferta de prueba de Getafe (piso de 85 m² confirmado y ubicado):

1. ¿Está cara mi oferta de Getafe? ¿Cuánto se alquilaría? → `valorar_oferta`
2. ¿Cuánto podría revalorizarse? → `valorar_oferta`
3. ¿Qué rentabilidad bruta tendría al precio que piden? → `valorar_oferta`
4. ¿Cómo es la zona? → `zona_de_oferta`
5. ¿Qué ofertas tengo guardadas? → `ofertas_guardadas`

## Resultado

| | qwen3:8b | qwen3:14b |
| --- | --- | --- |
| Herramientas correctas | 0/5 | 4/5 |
| Texto mostrado | 4/5 | 3/5 |
| A la primera | 4/5 | 2/5 |
| Tiempo medio | 5 s | 46 s |

- **8B:** no pidió ninguna herramienta, ni para listar las ofertas. Cuatro textos pasan porque no
  tienen cifras: piden «el identificador de la oferta» en lugar de buscarlo. En el quinto inventó
  marcadores (`{{fig:renta_…}}`) y se rechazó. En pruebas anteriores, con instrucciones un poco
  distintas, sí pedía las herramientas: su comportamiento cambia mucho con cambios pequeños.
- **14B:** elige bien las herramientas. Su respuesta a la primera pregunta es correcta y dice lo que
  tiene que decir (renta, precio estimado, lo que pide el anuncio, rentabilidad bruta, escenario
  base como tasa anual). Sus fallos son otros:
  - copia valores que ve en el resultado («−0.21% anual», «los próximos 10 años»);
  - se equivoca de ruta en la clave (`valuation.gross_yield_at_asking` en lugar de
    `offer.gross_yield_at_asking`; `appreciation_optimista` en lugar de `appreciation_optimistic`);
  - en la zona respondió que el identificador no era válido;
  - sigue escribiendo «menos» delante de una diferencia negativa.

## Ajustes del reintento con el 14B

| | 14B inicial | + clave más parecida | + descripción del campo |
| --- | --- | --- | --- |
| Herramientas correctas | 4/5 | 4/5 | 4/5 |
| Texto mostrado | 3/5 | 4/5 | 4/5 |
| A la primera | 2/5 | 2/5 | 2/5 |
| Tiempo medio | 46 s | 43 s | 39 s |

- **Clave más parecida:** si la clave no existe, el reintento propone la del plan con la misma
  parte final o una muy parecida («¿Querías decir `offer.gross_yield_at_asking`?»). La pregunta de
  la rentabilidad bruta pasó a mostrarse.
- **Descripción del campo:** un argumento que no valida devuelve la descripción del esquema
  («oferta_id (Identificador de la oferta, de ofertas_guardadas)»). En la zona, el modelo pasaba
  `{"oferta_id": "Getafe"}`; con el aviso nuevo tampoco pide la lista de ofertas y se rinde. Se
  mantiene porque no cuesta nada y puede servir a otros modelos.
- La revalorización sigue fallando: copia los valores que ve («−0.21% anual», «10 años»).

## Conclusiones

- El tamaño importa más que las instrucciones: el 14B resuelve lo que no arreglaban los ajustes de
  instrucciones sobre el 8B. Para el agente, el 8B no sirve.
- El 14B cabe en el Mac y tarda unos cuarenta y cinco segundos por pregunta: vale para desarrollo.
  Para la beta hace falta medir modelos mayores en el servidor de F7.
- Quedan dos fallos del 14B: copia los valores que ve en los resultados (el modelo recibe los
  valores para razonar, ADR-0019) y, con la pregunta de la zona, no pide la lista de ofertas antes
  de usar el identificador.
- Cinco preguntas sobre una oferta son pocas: el banco tiene que crecer con más ofertas y preguntas
  (F6.9) antes de decidir el modelo de producción.
